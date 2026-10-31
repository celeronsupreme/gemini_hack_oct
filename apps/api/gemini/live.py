"""Voice agent: ephemeral Live API tokens, the system prompt, and the four tool declarations.

The browser connects to the Live API directly with the ephemeral token (never the API key). Tool calls arrive in the
browser and are forwarded to POST /live/tool so the backend validates and writes them (tools.py)."""
from __future__ import annotations

import datetime as dt
from typing import Any

from contracts import LiveToken, Profile
from app.config import settings
from .client import get_client

DEFAULT_VOCAB = [
    "seizure", "aura", "focal", "tonic-clonic", "absence", "clobazam", "brivaracetam", "levetiracetam", "cenobamate",
    "lamotrigine", "carbamazepine", "oxcarbazepine", "lacosamide", "valproate", "midazolam", "buccal", "VNS magnet",
    "recovery position", "dribbling", "head to the side", "quiet and aware",
]

TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "log_seizure",
        "description": "Save one seizure to the diary once the carer has confirmed the read-back. Call it once per seizure.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {"type": "string", "description": "ISO 8601 local time; accept vague answers and convert (e.g. 'about ten minutes ago')."},
                "duration_s": {"type": "integer", "description": "Seconds. Omit if still going."},
                "duration_estimated": {"type": "boolean"},
                "still_going": {"type": "boolean"},
                "type": {"type": "string", "enum": ["aware", "staring", "impaired_awareness", "convulsive", "drop", "jerk", "unsure"]},
                "awareness": {"type": "string", "enum": ["kept", "impaired", "lost", "unknown"]},
                "warning_before": {"type": "boolean"},
                "warning_text": {"type": "string"},
                "context_tags": {"type": "array", "items": {"type": "string", "enum": ["shower_bath", "hot", "cold", "exercise", "travel", "upset", "school", "unwell", "period", "hungry", "screen", "late_night", "other"]}},
                "rescue_drug": {"type": "string"},
                "rescue_dose_mg": {"type": "number"},
                "recovered": {"type": "boolean"},
                "asleep_at_onset": {"type": "boolean"},
                "injury": {"type": "boolean"},
                "notes": {"type": "string", "description": "What the carer said, in their words, names removed."},
                "confidence": {"type": "string", "enum": ["certain", "probable", "guess"]},
            },
            "required": ["start_time", "type", "confidence"],
        },
    },
    {
        "name": "log_dose",
        "description": "Record that a scheduled dose was taken, taken late, or skipped.",
        "parameters": {
            "type": "object",
            "properties": {
                "drug": {"type": "string"}, "dose_mg": {"type": "number"},
                "scheduled_time": {"type": "string", "description": "ISO 8601 local time of the scheduled dose"},
                "taken_time": {"type": "string", "description": "ISO 8601 local time it was actually taken; omit if skipped"},
                "skipped": {"type": "boolean"}, "reason": {"type": "string"},
            },
            "required": ["drug", "scheduled_time"],
        },
    },
    {
        "name": "log_symptom",
        "description": "Record a warning sign or feeling-off report that is not itself a seizure (eyes going funny, feeling one coming).",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "time": {"type": "string", "description": "ISO 8601 local time"}}, "required": ["text", "time"]},
    },
    {
        "name": "get_todays_meds",
        "description": "Return today's scheduled doses with whether each has been logged as taken, so you can ask about the right one by name and time.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def system_instruction(profile: Profile, watching_triggers: list[str] | None = None, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    who = "the person you are caring for" if profile.role == "carer" else "you"
    name = profile.display_name or ("she" if profile.role == "carer" else "you")
    meds = "; ".join(f"{m.drug} {m.dose_mg:g} mg at {', '.join(m.times)}" for m in profile.medications if m.times) or "none on file"
    rescue = profile.rescue_plan.rescue_drug or "none"
    probes = "\n".join(f"- If relevant, ask once whether {t} was involved." for t in (watching_triggers or [])[:5])
    return f"""You are a calm, brief seizure-diary assistant. You are talking to a carer or to the person with epilepsy. You are not a clinician.
Today is {now.strftime('%A %d %B %Y')} and the time is {now.strftime('%H:%M')} (local). Greet first with one short sentence: "I'm listening. What happened?"

Your job is to get one complete record with the least talking.
1. First extract everything the person already said. Do not ask for anything they have told you.
2. Then ask for missing must-have fields, ONE question at a time, in this order: start time (accept "about ten minutes ago" and convert), how long it lasted or whether it is still going, what it looked like in plain words and whether {name} was aware, and whether there was any warning or aura beforehand.
3. If the person is not rushed, ask at most TWO of: what {name} was doing just before, when the last dose was taken, whether {name} is back to normal, whether {rescue} was given, whether {name} was asleep when it started, any injury, whether a period has started.
{probes}
4. Accept vague answers. Mark guesses as estimated. Never push for precision.
5. Read the record back in one sentence and wait for a yes before calling log_seizure. Example: "Logged: 19:15, about 90 seconds, head to the side, just after a hot shower. Right?"
6. Never give dosing or treatment advice. If asked, say to contact the epilepsy nurse and offer to note the question for the clinic report.
7. If a seizure is still going and has passed {profile.rescue_plan.emergency_minutes_convulsive} minutes (convulsive) or {profile.rescue_plan.emergency_minutes_other} minutes (any other type), stop logging and read the emergency plan: call {', '.join(profile.rescue_plan.call) or '999'}, recovery position, nothing in the mouth.
8. Keep every reply under 20 words unless reading the plan.

Medicines on file: {meds}. Rescue medicine: {rescue}.
Use log_dose when a dose is mentioned, log_symptom for warning signs that are not a seizure, get_todays_meds before asking about a dose.
Replace any personal names with role words (mum, brother, nurse) in anything you store."""


def create_live_token(profile: Profile, watching_triggers: list[str] | None = None, minutes: int = 30) -> LiveToken:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)
    vocab = sorted(set(DEFAULT_VOCAB) | set(profile.custom_vocabulary or []) | {m.drug for m in profile.medications})
    instr = system_instruction(profile, watching_triggers)
    client = get_client()
    if client is None:
        return LiveToken(token="mock-token", model=settings.live_model, expires_at=expires, system_instruction=instr, custom_vocabulary=vocab, tool_declarations=TOOL_DECLARATIONS, mock=True)
    token = client.auth_tokens.create(config={
        "uses": 1,
        "expire_time": expires.isoformat(),
        "new_session_expire_time": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2)).isoformat(),
        "live_connect_constraints": {"model": settings.live_model, "config": {"response_modalities": ["AUDIO"]}},
        "http_options": {"api_version": "v1alpha"},
    })
    return LiveToken(token=token.name, model=settings.live_model, expires_at=expires, system_instruction=instr, custom_vocabulary=vocab, tool_declarations=TOOL_DECLARATIONS, mock=False)
