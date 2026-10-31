"""Voice agent: ephemeral Live API tokens, the system prompt, and the four tool declarations.

The browser connects to the Live API directly with the ephemeral token (never the API key). Tool calls arrive in the
browser and are forwarded to POST /live/tool so the backend validates and writes them (tools.py)."""
from __future__ import annotations

import datetime as dt
from typing import Any

from contracts import LiveToken, Profile, SeizureEvent
from app.config import settings
from .client import get_client

DEFAULT_VOCAB = [
    "seizure", "aura", "focal", "tonic-clonic", "absence", "clobazam", "brivaracetam", "levetiracetam", "cenobamate",
    "lamotrigine", "carbamazepine", "oxcarbazepine", "lacosamide", "valproate", "midazolam", "buccal", "VNS magnet",
    "recovery position", "dribbling", "head to the side", "quiet and aware",
]

NOTE_DECLARATION: dict[str, Any] = {
    "name": "note",
    "description": "Show one fact you just heard on the carer's screen as a chip. Writes nothing; the carer saves the record themselves. Call it once per new fact, as soon as you hear it.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["what_happened", "awareness", "before", "medication", "new_factor"],
                     "description": "what_happened: what the seizure looked like. awareness: aware or not. before: something going on before it that is in her usual list. medication: a dose taken, late or missed. new_factor: something before it that is NOT in her usual list and might be worth tracking."},
            "label": {"type": "string", "description": "2 to 5 plain words, as a carer would say it: 'Head turned to one side', 'Aware throughout', 'Hot shower', '7 pm dose not taken yet', 'Skipped meal'."},
        },
        "required": ["kind", "label"],
    },
}

# Write tools stay available to POST /live/tool (and the tests), but the Live session is only offered note +
# get_todays_meds: per the design the assistant never saves; "Save to diary" commits the record.
WRITE_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "log_seizure",
        "description": "Save one seizure to the diary once the carer has confirmed the read-back. Call it once per seizure.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Id of the seizure the timer already logged, if the instructions give one. Pass it so this record is updated instead of creating a new one."},
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
]

GET_TODAYS_MEDS_DECLARATION: dict[str, Any] = {
    "name": "get_todays_meds",
    "description": "Return today's scheduled doses with whether each has been logged as taken, so you can ask about the right one by name and time.",
    "parameters": {"type": "object", "properties": {}},
}

TOOL_DECLARATIONS: list[dict[str, Any]] = [NOTE_DECLARATION, GET_TODAYS_MEDS_DECLARATION]

# Her usual list of things that happen before a seizure (the app's catalogue). Anything else is a new_factor.
USUAL_FACTORS = ["hot shower or bath", "missed dose", "poor sleep", "period", "stress", "travel", "late night", "tired",
                 "alcohol", "unwell", "skipped meal", "exercise", "upset", "school", "screens", "hot", "cold"]


def _timed_event_block(ev: SeizureEvent, tz: str) -> str:
    """Facts the one-tap timer already captured, so the voice agent never asks for them again."""
    from zoneinfo import ZoneInfo
    start = ev.start_time.astimezone(ZoneInfo(tz))
    if ev.duration_s:
        m, s = divmod(int(ev.duration_s), 60)
        dur = f"lasted {m} min {s} s" if m else f"lasted {s} s"
        dur += " (estimated)" if ev.duration_estimated else " (timed with the button, exact)"
    else:
        dur = "is still going or its length was not timed"
    return f"""
THIS SEIZURE IS ALREADY LOGGED by the app's timer: it started at {start.strftime('%H:%M')} on {start.strftime('%d %B')} and {dur}. Its id is "{ev.id}".
Do NOT ask when it started{' or how long it lasted' if ev.duration_s else ''}. Mention the time once in your read-back.
"""


def system_instruction(profile: Profile, watching_triggers: list[str] | None = None, now: dt.datetime | None = None,
                       timed_event: SeizureEvent | None = None) -> str:
    now = now or dt.datetime.now()
    name = profile.display_name or ("she" if profile.role == "carer" else "you")
    meds = "; ".join(f"{m.drug} {m.dose_mg:g} mg at {', '.join(m.times)}" for m in profile.medications if m.times) or "none on file"
    rescue = profile.rescue_plan.rescue_drug or "none"
    probes = "\n".join(f"- If relevant, ask once whether {t} was involved." for t in (watching_triggers or [])[:5])
    timed = _timed_event_block(timed_event, settings.timezone) if timed_event else ""
    first_missing = "what it looked like" if timed_event and timed_event.duration_s else ("how long it lasted" if timed_event else "start time")
    return f"""You are a calm, brief seizure-diary assistant. You are talking to a carer or to the person with epilepsy. You are not a clinician.
Today is {now.strftime('%A %d %B %Y')} and the time is {now.strftime('%H:%M')} (local).
The app has already shown "What happened?" on screen, and the person may start talking straight away. Do NOT greet and do NOT ask "what happened". Treat their first words as the answer and go straight to step 1.
{timed}
Your job is to get one complete record with the least talking.
0. The person's screen shows what you have picked up. Every time you hear a new fact, call note(kind, label) once for it, straight away and without mentioning it. Things before the seizure that are in her usual list ({', '.join(USUAL_FACTORS)}{', ' + ', '.join(watching_triggers) if watching_triggers else ''}) are kind "before"; anything else that happened before it and might matter is kind "new_factor". Never note the same fact twice.
1. First take in everything the person already said. Do not ask for anything they have told you. Briefly acknowledge what you heard.
2. Then ask for missing must-have fields, ONE question per turn (never two in one sentence), in this order, starting from {first_missing}: start time (accept "about ten minutes ago" and convert), how long it lasted or whether it is still going, what it looked like in plain words and whether {name} was aware, and whether there was any warning or aura beforehand.
3. If the person is not rushed, ask at most TWO of: what {name} was doing just before, when the last dose was taken, whether {name} is back to normal, whether {rescue} was given, whether {name} was asleep when it started, any injury, whether a period has started.
{probes}
4. Accept vague answers. Mark guesses as estimated. Never push for precision.
5. When you have enough, read the record back in one sentence and end with "Tap Save when you're happy." Example: "Got it: 19:15, about 90 seconds, quiet and aware, head to one side, just after a hot shower. Tap Save when you're happy." You never save anything yourself; the person taps Save. If they correct you, note the correction and read back again.
6. Never give dosing or treatment advice. If asked, say to contact the epilepsy nurse and offer to note the question for the clinic report.
7. If a seizure is still going and has passed {profile.rescue_plan.emergency_minutes_convulsive} minutes (convulsive) or {profile.rescue_plan.emergency_minutes_other} minutes (any other type), stop logging and read the emergency plan: call {', '.join(profile.rescue_plan.call) or '999'}, recovery position, nothing in the mouth.
8. Keep every reply under 20 words unless reading the plan.

Medicines on file: {meds}. Rescue medicine: {rescue}.
Call get_todays_meds before asking about a dose, then ask about the right one by name and time; note what you hear as kind "medication".
Replace any personal names with role words (mum, brother, nurse) in every note."""


def session_config(profile: Profile, watching_triggers: list[str] | None = None, with_vocabulary: bool = True,
                   timed_event: SeizureEvent | None = None) -> dict[str, Any]:
    """The FULL Live session config. It is locked into the ephemeral token so the server enforces it regardless of
    what the browser sends in its setup message (which is why a bare client config gave a generic chatbot)."""
    vocab = sorted(set(DEFAULT_VOCAB) | set(profile.custom_vocabulary or []) | {m.drug for m in profile.medications})
    cfg: dict[str, Any] = {
        "response_modalities": ["AUDIO"],
        "system_instruction": system_instruction(profile, watching_triggers, timed_event=timed_event),
        "tools": [{"function_declarations": TOOL_DECLARATIONS}],
        "input_audio_transcription": {"custom_vocabulary": vocab} if with_vocabulary else {},
        "output_audio_transcription": {},
        "context_window_compression": {"sliding_window": {}},
        "session_resumption": {},
    }
    return cfg


def create_live_token(profile: Profile, watching_triggers: list[str] | None = None, minutes: int = 30,
                      timed_event: SeizureEvent | None = None) -> LiveToken:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)
    vocab = sorted(set(DEFAULT_VOCAB) | set(profile.custom_vocabulary or []) | {m.drug for m in profile.medications})
    instr = system_instruction(profile, watching_triggers, timed_event=timed_event)
    client = get_client()
    if client is None:
        return LiveToken(token="mock-token", model=settings.live_model, expires_at=expires, system_instruction=instr, custom_vocabulary=vocab, tool_declarations=TOOL_DECLARATIONS, mock=True)
    last_error: Exception | None = None
    for with_vocab in (True, False):  # custom_vocabulary is newer than some SDK builds; fall back without it
        try:
            token = client.auth_tokens.create(config={
                "uses": 1,
                "expire_time": expires.isoformat(),
                "new_session_expire_time": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2)).isoformat(),
                "live_connect_constraints": {"model": settings.live_model, "config": session_config(profile, watching_triggers, with_vocab, timed_event)},
            })
            return LiveToken(token=token.name, model=settings.live_model, expires_at=expires, system_instruction=instr, custom_vocabulary=vocab if with_vocab else [], tool_declarations=TOOL_DECLARATIONS, mock=False)
        except Exception as e:  # noqa: BLE001
            last_error = e
            continue
    raise RuntimeError(f"ephemeral token creation failed: {last_error}")
