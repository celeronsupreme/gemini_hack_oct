"""Ad-hoc questions over the diary: Argon (gemini-4-argon) with code execution over a CSV of the person's events,
plus the engine's own numbers so the model explains rather than invents. Falls back to gemini-3.8-flash, then to a mock."""
from __future__ import annotations

import base64
import io
import json
import re

import pandas as pd

from contracts import AnalysisAnswer
from engine import EngineData
from app.config import settings
from .client import get_client

SYSTEM = """You are the analyst inside a seizure-diary app for one person. You answer questions about THEIR OWN diary only.
You are given a CSV of their seizures (local time), their medication timeline, and the engine's computed numbers.
Use the code execution tool to compute anything numeric; never estimate numbers in prose. Report counts and rates with the
window they come from. Say plainly when the data cannot answer (no dose times, no sleep data, too few events).
Never recommend changing medication; phrase findings as evidence to discuss with the clinician. No diagnostic labels.
Return JSON: {"answer": str (2-5 sentences), "numbers": object, "caveats": [str]}"""


def _events_csv(data: EngineData, days: int | None = None) -> str:
    ev = data.events
    if days:
        ev = ev[ev["start_time"] >= data.now() - pd.Timedelta(days=days)]
    cols = ["start_time", "duration_s", "type", "severity", "context_tags", "rescue_drug", "notes"]
    out = ev[cols].copy()
    out["start_time"] = out["start_time"].dt.strftime("%Y-%m-%d %H:%M")
    out["context_tags"] = out["context_tags"].apply(lambda t: "|".join(t or []))
    return out.to_csv(index=False)


def _mock_answer(question: str, data: EngineData, engine_numbers: dict) -> AnalysisAnswer:
    ev = data.events
    q = question.lower()
    last90 = ev[ev["start_time"] >= data.now() - pd.Timedelta(days=90)]
    numbers = {"events_last_90_days": int(len(last90)), "severe_last_90_days": int((last90["severity"] == "severe").sum()), **{k: v for k, v in engine_numbers.items() if isinstance(v, (int, float, str))}}
    if "evening" in q or "time of day" in q or "when" in q:
        hrs = last90["start_time"].dt.hour
        share = float(((hrs >= 12) & (hrs < 22)).mean() * 100) if len(hrs) else 0.0
        answer = f"In the last 90 days, {share:.0f}% of seizures started between midday and 10 pm; the busiest hour was {int(hrs.mode().iloc[0]) if len(hrs) else 'n/a'}:00."
        numbers["share_12_22_pct"] = round(share, 1)
    elif "dose" in q or "medic" in q:
        answer = "The diary holds dose schedules but no actual dose times, so I cannot test whether timing changed anything yet. Once doses are logged for a few weeks I can compare."
    else:
        answer = f"{len(last90)} seizures in the last 90 days, {numbers['severe_last_90_days']} of them severe. Ask about a time of day, a medication change, or a trigger for a specific comparison."
    return AnalysisAnswer(question=question, answer=answer, numbers=numbers, chart_png_base64=None, caveats=["Mock answer: Gemini is not configured. Numbers come from the engine, not a model."], model="mock", mock=True)


def ask(question: str, data: EngineData, engine_numbers: dict, medication_timeline_csv: str = "") -> AnalysisAnswer:
    client = get_client()
    if client is None:
        return _mock_answer(question, data, engine_numbers)
    csv_text = _events_csv(data)
    prompt = f"{SYSTEM}\n\nENGINE NUMBERS (trusted):\n{json.dumps(engine_numbers, default=str)[:4000]}\n\nMEDICATION TIMELINE CSV:\n{medication_timeline_csv[:6000]}\n\nEVENTS CSV:\n{csv_text}\n\nQUESTION: {question}"
    chart_b64 = None
    for model in (settings.analysis_model, settings.analysis_fallback_model):
        try:
            resp = client.models.generate_content(model=model, contents=prompt, config={"tools": [{"code_execution": {}}], "temperature": 0.2})
            text = ""
            for part in resp.candidates[0].content.parts:
                if getattr(part, "text", None):
                    text += part.text
                if getattr(part, "inline_data", None) and getattr(part.inline_data, "mime_type", "").startswith("image/"):
                    chart_b64 = base64.b64encode(part.inline_data.data).decode()
            m = re.search(r"\{.*\}", text, re.S)
            payload = json.loads(m.group(0)) if m else {"answer": text.strip(), "numbers": {}, "caveats": []}
            return AnalysisAnswer(question=question, answer=payload.get("answer", text.strip()), numbers=payload.get("numbers", {}) or {}, chart_png_base64=chart_b64, caveats=payload.get("caveats", []) or [], model=model, mock=False)
        except Exception as e:  # billing, quota, model not enabled: try the fallback, then mock
            last_error = str(e)
            continue
    out = _mock_answer(question, data, engine_numbers)
    out.caveats.append(f"Gemini call failed ({last_error[:120]}); showing engine numbers only.")
    return out
