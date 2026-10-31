"""Importers: the family's Excel diary, a generic CSV with a column mapping, and a Samsung Health export.

All importers return contract models with timezone-aware timestamps (Europe/London by default) and never
write to storage; the API layer decides what to keep.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from contracts import SeizureEvent, ImportPreview

TZ = "Europe/London"

# Plain-word app types <- phrases the family used over eight years. Order matters: first match wins.
LABEL_RULES: list[tuple[str, str, str]] = [
    # (substring to find in lowercased label, app type, severity)
    ("tonic", "convulsive", "severe"),
    ("head", "impaired_awareness", "severe"),
    ("slack", "impaired_awareness", "severe"),
    ("scared", "impaired_awareness", "severe"),
    ("quiet and aware", "aware", "mild"),
    ("very short", "aware", "mild"),
    ("aura", "aware", "mild"),
    ("talk", "aware", "mild"),
    ("absence", "staring", "mild"),
    ("deja", "aware", "mild"),
    ("déj", "aware", "mild"),
    ("non epileptic", "unsure", "mild"),
    ("nes", "unsure", "mild"),
    ("simple partial", "aware", "mild"),
    ("unsure", "unsure", "mild"),
]

CONTEXT_KEYWORDS: dict[str, str] = {
    "shower_bath": r"\bshower|\bbath\b|bathroom",
    "hot": r"\bhot\b|heat|warm|sweat|flushed",
    "cold": r"\bcold\b|freezing|chilly",
    "exercise": r"\bwalk|exercise|gym\b|trampoline|\brun\b|swim|bike|cycling|weights|danc|sport|gymnastics",
    "travel": r"\bcar\b|\btrain\b|driving|\bbus\b|journey|flight|travel",
    "upset": r"upset|stress|anxi|\brow\b|argument|crying|angry|worried|nervous|emotion",
    "school": r"school|lesson|class\b|homework|exam|college",
    "unwell": r"\bill\b|unwell|\bsick\b|cough|fever|headache|migraine|vomit|nausea|\bbug\b",
    "period": r"period|menstru",
    "hungry": r"hungry|not eaten|skipped (breakfast|lunch|dinner)",
    "screen": r"\btv\b|screen|phone|ipad|lights|flash",
    "late_night": r"late night|up late|didn.t sleep|no sleep|tired|exhaust",
}

# Real names never live in the repo. They are read from a gitignored file next to the diary,
# apps/api/data/redact_names.json: {"<Name>": "<role word>", ...}. Ask the team for it; without it nothing is redacted,
# so import_family_workbook refuses to run.
REDACT_NAMES_FILE = Path(__file__).resolve().parents[1] / "data" / "redact_names.json"


def _load_names() -> dict[str, str]:
    try:
        return json.loads(REDACT_NAMES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


ROLE_FOR_NAME = _load_names()
# Also catches possessives, with or without the apostrophe ("X's", "X’s", "Xs").
NAME_PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, ROLE_FOR_NAME)) + r")('s|’s|s)?\b") if ROLE_FOR_NAME else None
NHS_PATTERN = re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b")


def _role(m: re.Match) -> str:
    role = ROLE_FOR_NAME.get(m.group(1), "someone")
    if not m.group(2):
        return role
    return "her" if role == "she" else f"{role}'s"


def redact(text: str | None) -> str:
    if not text:
        return ""
    if NAME_PATTERN is not None:
        text = NAME_PATTERN.sub(_role, text)
    text = NHS_PATTERN.sub("[nhs number removed]", text)
    return text.strip()


def classify_label(label: str | None) -> tuple[str, str, bool]:
    """Return (app_type, severity, possibly_non_epileptic) for a free-text label."""
    if not isinstance(label, str) or not label.strip():
        return "unsure", "mild", False
    first = label.split("#")[0].strip().lower()
    nes = "non epileptic" in label.lower() or re.search(r"\bnes\b", label.lower()) is not None
    for needle, app_type, sev in LABEL_RULES:
        if needle in first:
            return app_type, sev, nes
    return "unsure", "mild", nes


def context_tags_from_text(text: str) -> list[str]:
    if not text:
        return []
    low = text.lower()
    return [tag for tag, pat in CONTEXT_KEYWORDS.items() if re.search(pat, low)]


def _to_time(v) -> dt.time | None:
    if isinstance(v, dt.time):
        return v
    if isinstance(v, dt.datetime):
        return v.time()
    if isinstance(v, str):
        m = re.match(r"^\s*(\d{1,2}):(\d{2})", v)
        if m:
            return dt.time(int(m.group(1)), int(m.group(2)))
    return None


def import_family_workbook(path: str | Path, tz: str = TZ) -> tuple[list[SeizureEvent], list[str]]:
    """Read the 'Seizure Data' tab of the family's workbook into SeizureEvent models.

    Returns (events, warnings). Rows without a seizure date are dropped; times default to 12:00 when missing
    (flagged in warnings and as confidence=guess).
    """
    if not ROLE_FOR_NAME:
        raise RuntimeError(f"{REDACT_NAMES_FILE} is missing, so names in the notes cannot be redacted. Ask the team for it.")
    import openpyxl  # local import keeps engine importable without openpyxl in other contexts

    zone = ZoneInfo(tz)
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    ws = wb["Seizure Data"] if "Seizure Data" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
    df = pd.DataFrame(rows[1:], columns=hdr)
    df = df[[c for c in df.columns if c]]
    df = df.dropna(how="all")
    warnings: list[str] = []
    events: list[SeizureEvent] = []
    missing_time = 0
    for _, r in df.iterrows():
        d = r.get("Seizure Date") or r.get("Date")
        if pd.isna(d):
            continue
        d = pd.Timestamp(d)
        t = _to_time(r.get("Time"))
        confidence = "probable"
        if t is None:
            t = dt.time(12, 0)
            missing_time += 1
            confidence = "guess"
        start = pd.Timestamp.combine(d.date(), t)
        start = start.tz_localize(zone, ambiguous=True, nonexistent="shift_forward")
        dur = r.get("Duration seconds (Calc)")
        dur = int(dur) if pd.notna(dur) else None
        label = r.get("Type")
        app_type, sev, nes = classify_label(label)
        sev_col = r.get("Seizure Severity (H/L)")
        if isinstance(sev_col, str) and sev_col.strip() in ("H", "L"):
            sev = "severe" if sev_col.strip() == "H" else "mild"
        notes = redact(r.get("Notes") if isinstance(r.get("Notes"), str) else "")
        if notes.lower().startswith("guess") or "guess" in notes.lower():
            confidence = "guess"
        clob = r.get("Clobazam Dose (10mg)")
        rescue = None
        try:
            if clob is not None and not pd.isna(clob) and float(clob) > 0:
                rescue = {"drug": "clobazam", "dose_mg": float(clob) * 10, "time": None}
        except (TypeError, ValueError):
            pass
        tags = context_tags_from_text(notes)
        period_flag = str(r.get("Day One of Period") or "").strip().lower() == "x"
        if period_flag and "period" not in tags:
            tags.append("period")
        warning = None
        if notes and re.search(r"felt (it|funny|one coming)|feel(ing)? funny|aura|warning|coming on", notes.lower()):
            warning = True
        events.append(SeizureEvent(
            id=str(uuid.uuid4()), start_time=start.to_pydatetime(), duration_s=dur,
            duration_estimated=confidence == "guess" or (dur is not None and dur % 30 == 0 and dur >= 60),
            type=app_type, severity=sev, awareness="kept" if app_type == "aware" else ("impaired" if app_type in ("impaired_awareness", "staring") else ("lost" if app_type == "convulsive" else "unknown")),
            asleep_at_onset=None, recovered_at=None, injury=None, incontinence=None,
            rescue_med=rescue, warning_before=warning, warning_text=None, context_tags=tags, notes=notes or None,
            original_label=str(label).strip() if isinstance(label, str) else None,
            who_logged="carer", confidence=confidence, possibly_non_epileptic=nes, source="import", transcript_hash=None,
        ))
    if missing_time:
        warnings.append(f"{missing_time} rows had no clock time; set to 12:00 and marked as guesses")
    warnings.append("Dates typed as d/m/y were trusted as entered; check any row where day and month could be swapped")
    warnings.append("Names in notes were replaced with role words; review before sharing")
    return events, warnings


def preview_from_events(events: list[SeizureEvent], source_name: str, warnings: list[str], sheets: list[str]) -> ImportPreview:
    labels: dict[str, str] = {}
    for e in events:
        if e.original_label and e.original_label not in labels:
            labels[e.original_label] = e.type
    return ImportPreview(
        job_id=str(uuid.uuid4()), source_name=source_name, sheets=sheets,
        column_mapping={"Seizure Date": "start_time (date)", "Time": "start_time (clock)", "Duration seconds (Calc)": "duration_s", "Type": "type + original_label", "Seizure Severity (H/L)": "severity", "Clobazam Dose (10mg)": "rescue_med", "Day One of Period": "context_tags: period", "Notes": "notes + context_tags"},
        assumptions=["Times are Europe/London local time", "A row with no time is a guess at midday", "Severity H = severe, L = mild; otherwise inferred from the type words"],
        warnings=warnings, preview_rows=events[:10], total_rows=len(events), label_mapping=labels,
    )


def import_generic_csv(path: str | Path, mapping: dict[str, str], tz: str = TZ, dayfirst: bool = True) -> tuple[list[SeizureEvent], list[str]]:
    """Generic CSV importer. `mapping` maps CSV column -> one of: start_time, date, time, duration_s, type, severity, notes."""
    zone = ZoneInfo(tz)
    df = pd.read_csv(path)
    inv = {v: k for k, v in mapping.items()}
    warnings: list[str] = []
    events: list[SeizureEvent] = []
    for _, r in df.iterrows():
        if "start_time" in inv:
            start = pd.to_datetime(r[inv["start_time"]], dayfirst=dayfirst, errors="coerce")
        else:
            d = pd.to_datetime(r.get(inv.get("date")), dayfirst=dayfirst, errors="coerce")
            t = _to_time(r.get(inv.get("time"))) if "time" in inv else None
            start = pd.Timestamp.combine(d.date(), t or dt.time(12, 0)) if pd.notna(d) else pd.NaT
        if pd.isna(start):
            continue
        if start.tzinfo is None:
            start = start.tz_localize(zone, ambiguous=True, nonexistent="shift_forward")
        label = r.get(inv.get("type")) if "type" in inv else None
        app_type, sev, nes = classify_label(label if isinstance(label, str) else None)
        if "severity" in inv and isinstance(r.get(inv["severity"]), str):
            s = r[inv["severity"]].strip().lower()
            sev = "severe" if s in ("h", "severe", "high") else ("mild" if s in ("l", "mild", "low") else sev)
        dur = r.get(inv.get("duration_s")) if "duration_s" in inv else None
        notes = redact(str(r.get(inv.get("notes")))) if "notes" in inv and pd.notna(r.get(inv.get("notes"))) else ""
        events.append(SeizureEvent(
            id=str(uuid.uuid4()), start_time=start.to_pydatetime(), duration_s=int(dur) if dur is not None and pd.notna(dur) else None,
            type=app_type, severity=sev, awareness="unknown", context_tags=context_tags_from_text(notes), notes=notes or None,
            original_label=str(label) if isinstance(label, str) else None, who_logged="import", confidence="probable",
            possibly_non_epileptic=nes, source="import",
        ))
    if dayfirst:
        warnings.append("Dates were read day-first (UK). Switch to month-first if the preview looks wrong.")
    return events, warnings
