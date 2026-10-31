"""Canonical in-memory data model the engine computes on.

The engine never touches the database or the network. It receives an `EngineData`
built from contract models (or from DataFrames with the canonical columns) and
returns contract models. Everything is timezone-aware; the person's local zone is
carried on `EngineData.tz`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

import pandas as pd

from contracts import CheckIn, Dose, SeizureEvent, Profile, MedicationSchedule, TriggerDefinition

EVENT_COLUMNS = [
    "id", "start_time", "duration_s", "duration_estimated", "type", "severity", "awareness",
    "asleep_at_onset", "recovered_at", "injury", "rescue_drug", "rescue_dose_mg", "warning_before",
    "context_tags", "notes", "original_label", "who_logged", "confidence", "possibly_non_epileptic", "source",
]
DOSE_COLUMNS = ["id", "drug", "dose_mg", "scheduled_time", "taken_time", "skipped", "reason", "source"]
CHECKIN_COLUMNS = [
    "id", "date", "sleep_bed_time", "sleep_wake_time", "sleep_quality", "stress", "mood", "fatigue",
    "feeling_off", "unwell", "period_started", "alcohol_units", "exercise", "big_event_tomorrow",
    "daily_trigger_flags", "notes", "source",
]

# Half-lives in hours (adult, ILAE TDM guideline ranges collapsed to a working midpoint).
HALF_LIFE_HOURS: dict[str, float] = {
    "brivaracetam": 9, "levetiracetam": 7, "clobazam": 20, "cenobamate": 50, "lamotrigine": 25,
    "carbamazepine": 14, "oxcarbazepine": 9, "valproate": 14, "lacosamide": 13, "phenytoin": 40,
    "topiramate": 21, "zonisamide": 63, "perampanel": 105, "clonazepam": 30, "diazepam": 40, "midazolam": 2,
}


def half_life_for(drug: str, override: float | None = None) -> float | None:
    if override:
        return override
    key = drug.strip().lower()
    for name, hl in HALF_LIFE_HOURS.items():
        if name in key:
            return hl
    return None


@dataclass
class EngineData:
    events: pd.DataFrame
    doses: pd.DataFrame
    checkins: pd.DataFrame
    symptoms: pd.DataFrame  # columns: time (tz-aware), text
    exposures: pd.DataFrame  # columns: name, start, end (tz-aware), source  — timed exposures (walks, showers...)
    profile: Profile
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("Europe/London"))

    # ---------- constructors ----------
    @classmethod
    def from_models(
        cls,
        events: Iterable[SeizureEvent],
        doses: Iterable[Dose] = (),
        checkins: Iterable[CheckIn] = (),
        profile: Profile | None = None,
        symptoms: Sequence[tuple[datetime, str]] = (),
        exposures: Sequence[tuple[str, datetime, datetime, str]] = (),
        tz: str = "Europe/London",
    ) -> "EngineData":
        zone = ZoneInfo(tz)
        ev_rows = []
        for e in events:
            ev_rows.append({
                "id": e.id, "start_time": pd.Timestamp(e.start_time).tz_convert(zone),
                "duration_s": e.duration_s, "duration_estimated": e.duration_estimated, "type": str(e.type.value if hasattr(e.type, "value") else e.type),
                "severity": str(e.severity.value if hasattr(e.severity, "value") else e.severity),
                "awareness": str(e.awareness.value if e.awareness and hasattr(e.awareness, "value") else (e.awareness or "unknown")),
                "asleep_at_onset": e.asleep_at_onset,
                "recovered_at": pd.Timestamp(e.recovered_at).tz_convert(zone) if e.recovered_at else pd.NaT,
                "injury": e.injury, "rescue_drug": e.rescue_med.drug if e.rescue_med else None,
                "rescue_dose_mg": e.rescue_med.dose_mg if e.rescue_med else None, "warning_before": e.warning_before,
                "context_tags": [str(t.value if hasattr(t, "value") else t) for t in (e.context_tags or [])],
                "notes": e.notes or "", "original_label": e.original_label,
                "who_logged": str(e.who_logged.value if hasattr(e.who_logged, "value") else e.who_logged),
                "confidence": str(e.confidence.value if hasattr(e.confidence, "value") else e.confidence),
                "possibly_non_epileptic": bool(e.possibly_non_epileptic), "source": str(e.source.value if hasattr(e.source, "value") else e.source),
            })
        ev = pd.DataFrame(ev_rows, columns=EVENT_COLUMNS)
        if len(ev):
            ev["start_time"] = pd.to_datetime(ev["start_time"], utc=True).dt.tz_convert(zone)
            ev = ev.sort_values("start_time").reset_index(drop=True)
        else:
            ev["start_time"] = pd.Series(dtype=f"datetime64[ns, {tz}]")
        do_rows = [{
            "id": d.id, "drug": d.drug, "dose_mg": d.dose_mg,
            "scheduled_time": pd.Timestamp(d.scheduled_time).tz_convert(zone),
            "taken_time": pd.Timestamp(d.taken_time).tz_convert(zone) if d.taken_time else pd.NaT,
            "skipped": bool(d.skipped), "reason": d.reason, "source": str(d.source.value if hasattr(d.source, "value") else d.source),
        } for d in doses]
        do = pd.DataFrame(do_rows, columns=DOSE_COLUMNS)
        if len(do):
            do["scheduled_time"] = pd.to_datetime(do["scheduled_time"], utc=True).dt.tz_convert(zone)
            do["taken_time"] = pd.to_datetime(do["taken_time"], utc=True).dt.tz_convert(zone)
        ci_rows = []
        for c in checkins:
            ci_rows.append({
                "id": c.id, "date": pd.Timestamp(c.date),
                "sleep_bed_time": pd.Timestamp(c.sleep_bed_time).tz_convert(zone) if c.sleep_bed_time else pd.NaT,
                "sleep_wake_time": pd.Timestamp(c.sleep_wake_time).tz_convert(zone) if c.sleep_wake_time else pd.NaT,
                "sleep_quality": c.sleep_quality, "stress": c.stress, "mood": c.mood, "fatigue": c.fatigue,
                "feeling_off": c.feeling_off, "unwell": c.unwell, "period_started": c.period_started,
                "alcohol_units": c.alcohol_units, "exercise": c.exercise, "big_event_tomorrow": c.big_event_tomorrow,
                "daily_trigger_flags": dict(c.daily_trigger_flags or {}), "notes": c.notes or "",
                "source": str(c.source.value if hasattr(c.source, "value") else c.source),
            })
        ci = pd.DataFrame(ci_rows, columns=CHECKIN_COLUMNS)
        sy = pd.DataFrame([{"time": pd.Timestamp(t).tz_convert(zone), "text": s} for t, s in symptoms], columns=["time", "text"])
        ex = pd.DataFrame([{"name": n, "start": pd.Timestamp(a).tz_convert(zone), "end": pd.Timestamp(b).tz_convert(zone), "source": src} for n, a, b, src in exposures], columns=["name", "start", "end", "source"])
        return cls(events=ev, doses=do, checkins=ci, symptoms=sy, exposures=ex, profile=profile or default_profile(), tz=zone)

    # ---------- derived series ----------
    def daily_counts(self, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None, severe_only: bool = False) -> pd.Series:
        """Seizures per local calendar day on a continuous index (zero-filled)."""
        ev = self.events
        if severe_only:
            ev = ev[ev["severity"] == "severe"]
        if len(self.events) == 0:
            idx = pd.date_range(start or pd.Timestamp.now(tz=self.tz).normalize(), end or pd.Timestamp.now(tz=self.tz).normalize(), freq="D", tz=self.tz)
            return pd.Series(0, index=idx.tz_localize(None), dtype=int)
        days = ev["start_time"].dt.tz_localize(None).dt.normalize() if len(ev) else pd.Series(dtype="datetime64[ns]")
        first = (start.tz_localize(None) if start is not None and start.tzinfo else start) if start is not None else self.events["start_time"].min().tz_localize(None).normalize()
        last = (end.tz_localize(None) if end is not None and end.tzinfo else end) if end is not None else self.events["start_time"].max().tz_localize(None).normalize()
        idx = pd.date_range(first.normalize(), last.normalize(), freq="D")
        counts = days.value_counts().reindex(idx, fill_value=0).astype(int)
        return counts

    def events_between(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        ev = self.events
        return ev[(ev["start_time"] >= start) & (ev["start_time"] < end)]

    def now(self) -> pd.Timestamp:
        return pd.Timestamp.now(tz=self.tz)


def to_ns(idx) -> "np.ndarray":
    """UTC nanoseconds since epoch for any tz-aware DatetimeIndex/Series, regardless of pandas unit."""
    import numpy as np
    di = pd.DatetimeIndex(idx)
    if di.tz is None:
        raise ValueError("to_ns expects tz-aware timestamps")
    return di.tz_convert("UTC").as_unit("ns").asi8


def default_profile() -> Profile:
    return Profile(
        display_name="",
        role="carer",
        medications=[],
        rescue_plan={"rescue_drug": None, "rescue_dose_mg": None, "emergency_minutes_convulsive": 5, "emergency_minutes_other": 10, "call": ["999"], "notes": None},
        sleep_window={"start": "00:00", "end": "07:00"},
        custom_vocabulary=[],
        consent={"gemini_processing": False, "accepted_at": None},
    )


def ensure_tz(ts: datetime | pd.Timestamp | str, tz: ZoneInfo) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
    return t.tz_convert(tz)
