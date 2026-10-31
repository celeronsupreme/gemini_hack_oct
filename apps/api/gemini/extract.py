"""Transcript -> DiaryEntryBatch. One structured-output call on gemini-3.8-flash over the full two-sided transcript.
The result is reconciled with rows the tools already wrote (tool row wins; extractor fills blanks)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

from contracts import DiaryEntryBatch, SeizureEvent
from engine.importer import context_tags_from_text, redact
from app.config import settings
from .client import get_client

PROMPT = """You turn a conversation between a seizure-diary assistant and a carer into structured records.
Rules: use only what was said; never invent times or durations; if a duration was a guess, set duration_estimated true;
start_time must be an ISO 8601 datetime with the local offset {offset}; today is {today}; replace personal names with role words.
Return every seizure, dose and warning symptom mentioned, plus open_questions for anything the assistant should have asked but did not.
Transcript:
{transcript}"""

SEVERE_TYPES = {"impaired_awareness", "convulsive", "drop"}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _mock_extract(transcript: str, now: dt.datetime) -> DiaryEntryBatch:
    """A deterministic heuristic extractor so the demo works offline."""
    t = transcript.lower()
    m = re.search(r"(\d{1,2})[:.](\d{2})", t)
    start = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0) if m else now - dt.timedelta(minutes=10)
    dur = None; est = True
    md = re.search(r"(\d+(?:\.\d+)?)\s*(minute|min)", t)
    ms = re.search(r"(\d+)\s*(second|sec)", t)
    if md:
        dur = int(float(md.group(1)) * 60)
    elif ms:
        dur = int(ms.group(1))
    if "a minute and a half" in t or "minute and a half" in t:
        dur = 90
    typ = "impaired_awareness" if re.search(r"head (went|to the side)|dribbl|saliva|couldn.t speak|unresponsive", t) else ("convulsive" if re.search(r"shak|jerk|convuls|tonic", t) else ("aware" if re.search(r"aware|quiet|knew what was", t) else "unsure"))
    tags = context_tags_from_text(transcript)
    ev = SeizureEvent(start_time=start, duration_s=dur, duration_estimated=est, type=typ, severity="severe" if typ in SEVERE_TYPES else "mild",
                      awareness="impaired" if typ == "impaired_awareness" else ("kept" if typ == "aware" else "unknown"),
                      warning_before=True if re.search(r"felt (it|one) coming|warning|aura|funny", t) else None, context_tags=tags,
                      notes=redact(transcript)[:500], who_logged="carer", confidence="probable" if m else "guess", source="voice", transcript_hash=_hash(transcript))
    questions = []
    if dur is None:
        questions.append("How long did it last?")
    if not re.search(r"dose|tablet|cenobamate|brivaracetam|medic", t):
        questions.append("Was the last dose taken on time?")
    return DiaryEntryBatch(seizures=[ev], doses=[], checkin=None, symptoms=[], open_questions=questions, transcript_hash=_hash(transcript))


def extract(transcript: str, now: dt.datetime | None = None) -> DiaryEntryBatch:
    from zoneinfo import ZoneInfo
    now = now or dt.datetime.now(ZoneInfo(settings.timezone))
    client = get_client()
    if client is None:
        return _mock_extract(transcript, now)
    offset = now.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    resp = client.models.generate_content(
        model=settings.extract_model,
        contents=PROMPT.format(offset=offset, today=now.strftime("%Y-%m-%d"), transcript=transcript),
        # response_json_schema passes the JSON Schema through untouched; response_schema rejects additionalProperties
        # (used throughout the contracts) on the Developer API.
        config={"response_mime_type": "application/json", "response_json_schema": DiaryEntryBatch.model_json_schema(), "temperature": 0},
    )
    batch = DiaryEntryBatch.model_validate_json(resp.text)
    h = _hash(transcript)
    batch.transcript_hash = h
    for s in batch.seizures:
        s.transcript_hash = h
        s.notes = redact(s.notes)
        if s.source is None or str(s.source) != "voice":
            s.source = "voice"
        if not s.context_tags and s.notes:
            s.context_tags = context_tags_from_text(s.notes)
    return batch
