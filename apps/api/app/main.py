"""FastAPI entry point. Every read endpoint accepts `?mock=1` and then serves the fixture of the same name from
packages/contracts/fixtures, so the web client can be built with the API half-finished."""
from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contracts import (AnalysisAnswer, BaselineStats, CheckIn, ClinicReport, DiaryEntryBatch, Dose, HourlyStats, ImportPreview, LiveToken,
                       MonthlyStats, Profile, RiskNow, SeizureEvent, TriggerDefinition, TriggerTest)
from engine import backtest as run_backtest
from engine.importer import import_family_workbook, import_generic_csv, preview_from_events
from gemini import analysis as gemini_analysis, extract as gemini_extract, live as gemini_live, tools as gemini_tools
from . import service, store
from .config import settings

log = logging.getLogger("api")
app = FastAPI(title="Seizure diary API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins + ["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

_import_jobs: dict[str, dict[str, Any]] = {}


def fixture(name: str):
    p = settings.fixtures_dir / f"{name}.json"
    if not p.exists():
        raise HTTPException(404, f"no fixture {name}")
    return JSONResponse(json.loads(p.read_text()))


@app.get("/health")
def health():
    return {"ok": True, "gemini": settings.gemini_enabled, "models": {"live": settings.live_model, "extract": settings.extract_model, "analysis": settings.analysis_model}, "counts": store.counts(), "data_version": store.data_version()}


# ---------- profile ----------
@app.get("/profile", response_model=Profile)
def get_profile(mock: int = 0):
    return fixture("profile") if mock else store.get_profile()


@app.put("/profile", response_model=Profile)
def put_profile(p: Profile):
    store.save_profile(p); service.invalidate()
    return p


# ---------- records ----------
@app.get("/events", response_model=list[SeizureEvent])
def get_events(mock: int = 0, from_: str | None = Query(None, alias="from"), to: str | None = None, limit: int = 500):
    if mock:
        return fixture("events")
    data = service.engine_data()
    start = pd.Timestamp(from_).tz_localize(data.tz) if from_ and pd.Timestamp(from_).tzinfo is None else (pd.Timestamp(from_) if from_ else None)
    end = pd.Timestamp(to).tz_localize(data.tz) if to and pd.Timestamp(to).tzinfo is None else (pd.Timestamp(to) if to else None)
    evs = store.list_events(start, end)
    return evs[-limit:]


@app.post("/events", response_model=SeizureEvent)
def post_event(e: SeizureEvent):
    saved = store.add_events([e])[0]; service.invalidate()
    return saved


@app.post("/events/tap", response_model=SeizureEvent)
def tap_event(body: dict = Body(default={})):
    """The one-tap 'just had one': timestamps now, everything else to be filled in later."""
    data = service.engine_data()
    e = SeizureEvent(start_time=data.now().to_pydatetime(), still_going=bool(body.get("still_going", True)), type="unsure", severity="mild", awareness="unknown",
                     who_logged="carer" if store.get_profile().role == "carer" else "patient", confidence="probable", source="tap")
    saved = store.add_events([e])[0]; service.invalidate()
    return saved


@app.patch("/events/{event_id}", response_model=SeizureEvent)
def patch_event(event_id: str, patch: dict = Body(...)):
    evs = {e.id: e for e in store.list_events()}
    if event_id not in evs:
        raise HTTPException(404, "event not found")
    merged = {**evs[event_id].model_dump(), **patch}
    if "type" in patch and "severity" not in patch:
        merged["severity"] = "severe" if patch["type"] in ("impaired_awareness", "convulsive", "drop") else "mild"
    updated = SeizureEvent.model_validate(merged)
    store.add_events([updated]); service.invalidate()
    return updated


@app.post("/doses", response_model=Dose)
def post_dose(d: Dose):
    saved = store.add_doses([d])[0]; service.invalidate()
    return saved


@app.get("/doses", response_model=list[Dose])
def get_doses(mock: int = 0, from_: str | None = Query(None, alias="from"), to: str | None = None):
    if mock:
        return fixture("doses")
    return store.list_doses(from_, to)


@app.post("/checkins", response_model=CheckIn)
def post_checkin(c: CheckIn):
    saved = store.add_checkins([c])[0]; service.invalidate()
    return saved


@app.get("/checkins", response_model=list[CheckIn])
def get_checkins(mock: int = 0):
    return fixture("checkins") if mock else store.list_checkins()


# ---------- engine ----------
@app.get("/risk/now", response_model=RiskNow)
def risk_now(mock: int = 0, at: str | None = None):
    return fixture("risk_now") if mock else service.risk_now(at)


@app.get("/stats/hourly", response_model=HourlyStats)
def stats_hourly(mock: int = 0, at: str | None = None, window_days: int = 365):
    return fixture("stats_hourly") if mock else service.hourly(at, window_days)


@app.get("/stats/monthly", response_model=MonthlyStats)
def stats_monthly(mock: int = 0):
    return fixture("stats_monthly") if mock else service.monthly()


@app.get("/stats/baseline", response_model=BaselineStats)
def stats_baseline(mock: int = 0, at: str | None = None, window_days: int = 90):
    return fixture("stats_baseline") if mock else service.baseline(at, window_days)


@app.get("/stats/backtest")
def stats_backtest(start: str = "2024-01-01", end: str = "2026-08-24"):
    return run_backtest(service.engine_data(), start, end)


# ---------- triggers ----------
@app.get("/triggers", response_model=list[TriggerTest])
def get_triggers(mock: int = 0):
    return fixture("triggers") if mock else service.list_trigger_tests()


@app.get("/triggers/definitions", response_model=list[TriggerDefinition])
def get_trigger_definitions():
    return store.list_trigger_definitions()


@app.post("/triggers", response_model=TriggerTest)
def post_trigger(d: TriggerDefinition):
    return service.add_trigger(d)


@app.post("/triggers/test", response_model=list[TriggerTest])
def retest_triggers(body: dict = Body(default={})):
    return service.run_trigger_tests(only=body.get("only"), at=body.get("at"))


@app.post("/triggers/{trigger_id}/archive")
def archive_trigger(trigger_id: str):
    defs = {d.id: d for d in store.list_trigger_definitions()}
    if trigger_id not in defs:
        raise HTTPException(404, "trigger not found")
    store.upsert_trigger_definition(defs[trigger_id].model_copy(update={"archived": True}))
    return {"ok": True}


# ---------- report ----------
@app.get("/report/clinic", response_model=ClinicReport)
def report_clinic(mock: int = 0, window: int = 90, at: str | None = None):
    return fixture("report_clinic") if mock else service.clinic_report(window_days=window, at=at)


@app.put("/report/questions")
def put_questions(body: dict = Body(...)):
    store.set_kv("clinic_questions", body.get("questions", []))
    return {"ok": True}


# ---------- voice ----------
@app.post("/live/token", response_model=LiveToken)
def live_token(body: dict = Body(default={}), mock: int = 0):
    """Body may carry {event_id}: the seizure the one-tap timer logged, so the agent starts from its time and duration."""
    if mock:
        return fixture("live_token")
    watching = [t.trigger for t in service.list_trigger_tests() if str(t.rung.value if hasattr(t.rung, "value") else t.rung) in ("watching", "emerging")]
    timed = next((e for e in store.list_events() if e.id == body.get("event_id")), None) if body.get("event_id") else None
    return gemini_live.create_live_token(store.get_profile(), watching, timed_event=timed)


@app.post("/live/tool")
def live_tool(body: dict = Body(...)):
    """The browser forwards each Live function call here: {name, args, id}. Returns the function response payload."""
    return {"id": body.get("id"), "name": body.get("name"), "response": gemini_tools.handle(body.get("name", ""), body.get("args") or {})}


@app.post("/transcripts/extract", response_model=DiaryEntryBatch)
def transcripts_extract(body: dict = Body(...), mock: int = 0):
    if mock:
        return fixture("extract")
    return gemini_extract.extract(body.get("transcript", ""))


@app.post("/transcripts/commit", response_model=list[SeizureEvent])
def transcripts_commit(batch: DiaryEntryBatch):
    """Save a confirmed batch. Seizures already written by tool calls (same transcript_hash) are updated, not duplicated."""
    existing = [e for e in store.list_events() if e.transcript_hash and batch.transcript_hash and e.transcript_hash == batch.transcript_hash]
    saved = []
    for i, s in enumerate(batch.seizures):
        if i < len(existing):
            merged = existing[i].model_copy(update={k: v for k, v in s.model_dump().items() if v not in (None, [], "") and k != "id"})
            saved.extend(store.add_events([merged]))
        else:
            saved.extend(store.add_events([s]))
    if batch.doses:
        store.add_doses(batch.doses)
    if batch.checkin:
        store.add_checkins([batch.checkin])
    for sy in batch.symptoms:
        store.add_symptom(sy.time, sy.text)
    service.invalidate()
    return saved


# ---------- analysis ----------
@app.post("/analysis/ask", response_model=AnalysisAnswer)
def analysis_ask(body: dict = Body(...), mock: int = 0):
    if mock:
        return fixture("analysis")
    data = service.engine_data()
    numbers = {"risk_now": service.risk_now().model_dump(mode="json"), "baseline": service.baseline().model_dump(mode="json"), "hourly_peak": service.hourly().peak_hour}
    med_csv = (settings.db_path.parent / "medication_timeline.csv").read_text() if (settings.db_path.parent / "medication_timeline.csv").exists() else ""
    return gemini_analysis.ask(body.get("question", ""), data, numbers, med_csv)


# ---------- import ----------
@app.post("/import/preview", response_model=ImportPreview)
async def import_preview(file: UploadFile = File(...), mock: int = 0):
    if mock:
        return fixture("import_preview")
    suffix = Path(file.filename or "upload").suffix.lower()
    tmp = Path(tempfile.mkdtemp()) / (file.filename or "upload")
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    if suffix in (".xlsx", ".xlsm"):
        events, warnings = import_family_workbook(tmp)
        sheets = ["Seizure Data"]
    elif suffix == ".csv":
        head = pd.read_csv(tmp, nrows=5)
        mapping = {}
        for c in head.columns:
            lc = c.lower()
            if "start" in lc or lc in ("datetime", "timestamp"):
                mapping[c] = "start_time"
            elif lc.startswith("date") or lc == "seizure date":
                mapping[c] = "date"
            elif lc.startswith("time"):
                mapping[c] = "time"
            elif "duration" in lc:
                mapping[c] = "duration_s"
            elif "type" in lc:
                mapping[c] = "type"
            elif "sever" in lc:
                mapping[c] = "severity"
            elif "note" in lc:
                mapping[c] = "notes"
        events, warnings = import_generic_csv(tmp, mapping)
        sheets = ["csv"]
    else:
        raise HTTPException(400, "upload a .xlsx or .csv")
    preview = preview_from_events(events, file.filename or "upload", warnings, sheets)
    _import_jobs[preview.job_id] = {"events": events}
    return preview


@app.post("/import/commit")
def import_commit(body: dict = Body(...)):
    job = _import_jobs.pop(body.get("job_id", ""), None)
    if not job:
        raise HTTPException(404, "import job not found or already committed")
    label_map = body.get("label_mapping") or {}
    events = job["events"]
    if label_map:
        events = [e.model_copy(update={"type": label_map.get(e.original_label, e.type)}) for e in events]
    if body.get("replace"):
        store.reset_all()
    store.add_events(events); service.invalidate()
    return {"imported": len(events)}
