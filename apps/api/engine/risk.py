"""Risk over the next few hours: a transparent points score, calibrated per person, explained in words.

Design rules (see the brief, section "Risk score design"):
- deterministic; Gemini explains the output, never produces it
- every point has a reason the user can read
- thresholds are set per person so "high" covers about 15% of their hours over the trailing 90 days
- overnight hours are reported as "no data", never "low"
- under 30 events the engine is in learning mode and uses only today's count and time since the last seizure
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from contracts import RiskNow, RiskReason
from .data import EngineData, ensure_tz, half_life_for, to_ns
from .stats import LEARNING_MODE_MIN_EVENTS

DISCLAIMER = "A pattern from your own diary over the next few hours, not a prediction. Low never means safe. Research prototype."
HIGH_SHARE = 0.15
MEDIUM_SHARE = 0.50
HORIZON_HOURS = 3
BAND_CAP = 4.0
# Weights for the two "what happened today" components. On the demo diary the hour band carries most of the signal;
# these stay small so they explain rather than dominate. (Walk-forward AUC on 2024-26: 0.69 with these, 0.71 without.)
TODAY_COUNT_WEIGHT = 0.3
RECENT_GAP_WEIGHT = 0.3

COMPONENTS = ["hour_band", "today_count", "recent_gap", "week_vs_baseline", "dose_overdue", "dose_skipped", "feeling_off", "stress", "short_sleep"]


def _in_sleep_window(hours: np.ndarray, start: str, end: str) -> np.ndarray:
    s = int(start.split(":")[0]); e = int(end.split(":")[0])
    if s <= e:
        return (hours >= s) & (hours < e)
    return (hours >= s) | (hours < e)


def forward_band(hist: np.ndarray, n: int, horizon: int = HORIZON_HOURS, cap: float = BAND_CAP) -> np.ndarray:
    """Points for each clock hour: share of seizures starting in [h, h+horizon) relative to a flat day, 0.1 steps, capped."""
    fwd = np.array([sum(hist[(h + k) % 24] for k in range(horizon)) for h in range(24)], dtype=float)
    vs_flat = (fwd / n) * (24 / horizon) if n else np.zeros(24)
    return np.clip(np.round(vs_flat, 1), 0, cap)


def hour_histogram(data: EngineData, as_of: pd.Timestamp, window_days: int = 365) -> tuple[np.ndarray, int]:
    ev = data.events_between(as_of - pd.Timedelta(days=window_days), as_of)
    counts = ev["start_time"].dt.hour.value_counts().reindex(range(24), fill_value=0).to_numpy(dtype=float)
    return counts, int(counts.sum())


def score_grid(data: EngineData, times: pd.DatetimeIndex, as_of: pd.Timestamp | None = None, trigger_rungs: dict[str, str] | None = None) -> pd.DataFrame:
    """Score every timestamp in `times` (tz-aware). Returns one row per time with each component's points."""
    as_of = as_of or (times[-1] if len(times) else data.now())
    trigger_rungs = trigger_rungs or {}
    tz = data.tz
    ev_times = data.events["start_time"].sort_values().to_numpy() if len(data.events) else np.array([], dtype="datetime64[ns]")
    ev_utc = to_ns(data.events["start_time"].sort_values()) if len(data.events) else np.array([], dtype="int64")
    t_utc = to_ns(times)
    local = pd.DatetimeIndex(times).tz_convert(tz)
    hours = local.hour.to_numpy()
    midnight_utc = to_ns(local.normalize())

    # --- counts via searchsorted on UTC nanoseconds ---
    idx_t = np.searchsorted(ev_utc, t_utc, side="left")
    idx_mid = np.searchsorted(ev_utc, midnight_utc, side="left")
    today_count = idx_t - idx_mid
    week_ns = int(pd.Timedelta(days=7).value)
    idx_7 = np.searchsorted(ev_utc, t_utc - week_ns, side="left")
    last7 = idx_t - idx_7
    last_before = np.where(idx_t > 0, ev_utc[np.clip(idx_t - 1, 0, max(len(ev_utc) - 1, 0))] if len(ev_utc) else 0, -1)
    hours_since_last = np.where(idx_t > 0, (t_utc - last_before) / 3.6e12, np.inf)

    # --- hour band from the person's own histogram ---
    hist, n_hist = hour_histogram(data, as_of)
    if n_hist >= LEARNING_MODE_MIN_EVENTS:
        # forward-looking: the share of the person's seizures that start in the next HORIZON_HOURS, against a flat day.
        band = forward_band(hist, n_hist)[hours]
    else:
        band = np.zeros(len(times))

    # --- week vs baseline (weekly sums over trailing 90 days as of as_of) ---
    end_day = as_of.tz_convert(tz).tz_localize(None).normalize()
    daily = data.daily_counts(start=end_day - pd.Timedelta(days=90), end=end_day)
    weekly = daily.rolling(7).sum().dropna()
    p50 = float(weekly.quantile(0.5)) if len(weekly) else 0.0
    p75 = float(weekly.quantile(0.75)) if len(weekly) else 0.0
    week_pts = np.where(last7 > p75, 1.0, np.where(last7 > p50, 0.5, 0.0)) if n_hist >= LEARNING_MODE_MIN_EVENTS else np.zeros(len(times))

    df = pd.DataFrame({
        "time": times, "hour": hours, "today_count_n": today_count, "last7_n": last7, "hours_since_last_n": hours_since_last,
        "hour_band": band, "today_count": np.minimum(today_count, 2).astype(float) * TODAY_COUNT_WEIGHT, "recent_gap": np.where(hours_since_last < 6, RECENT_GAP_WEIGHT, 0.0), "week_vs_baseline": week_pts,
        "dose_overdue": 0.0, "dose_skipped": 0.0, "feeling_off": 0.0, "stress": 0.0, "short_sleep": 0.0,
    })

    # --- doses: active only if the person logs doses (any dose record in the 14 days before as_of) ---
    doses = data.doses
    if len(doses) and (doses["scheduled_time"] >= as_of - pd.Timedelta(days=14)).any() and data.profile.medications:
        dose_overdue = np.zeros(len(times)); dose_skipped = np.zeros(len(times))
        for med in data.profile.medications:
            if med.as_needed or not med.times:
                continue
            hl = half_life_for(med.drug, med.half_life_hours) or 12.0
            grace = pd.Timedelta(hours=0.25 * hl)
            recs = doses[doses["drug"].str.lower().str.contains(med.drug.lower().split()[0])]
            for i, t in enumerate(local):
                for hhmm in med.times:
                    hh, mm = (int(x) for x in hhmm.split(":"))
                    sched = t.normalize() + pd.Timedelta(hours=hh, minutes=mm)
                    if sched > t:
                        continue
                    near = recs[(recs["scheduled_time"] - sched).abs() <= pd.Timedelta(hours=1)]
                    if len(near) and near["skipped"].any():
                        dose_skipped[i] = 2.0
                    elif len(near) and near["taken_time"].notna().any():
                        continue
                    elif t - sched > grace:
                        dose_overdue[i] = max(dose_overdue[i], 1.0)
        df["dose_overdue"] = dose_overdue; df["dose_skipped"] = dose_skipped

    # --- check-ins: feeling off, stress, short sleep ---
    ci = data.checkins
    if len(ci):
        ci_by_day = ci.set_index(ci["date"].dt.normalize())
        day_index = pd.DatetimeIndex(local.normalize().tz_localize(None))
        fo = ci_by_day["feeling_off"].reindex(day_index).fillna(False).astype(bool).to_numpy()
        df["feeling_off"] = np.where(fo, 2.0, 0.0)
        if trigger_rungs.get("stress") in ("emerging", "supported"):
            st = ci_by_day["stress"].reindex(day_index).to_numpy(dtype=float)
            df["stress"] = np.where(np.nan_to_num(st, nan=0.0) >= 7, 0.5, 0.0)
        if ci["sleep_bed_time"].notna().sum() >= 14:
            dur = (ci["sleep_wake_time"] - ci["sleep_bed_time"]).dt.total_seconds() / 3600
            p25 = float(dur.dropna().quantile(0.25))
            dur_by_day = pd.Series(dur.to_numpy(), index=ci["date"].dt.normalize()).reindex(day_index).to_numpy(dtype=float)
            df["short_sleep"] = np.where(np.nan_to_num(dur_by_day, nan=99.0) < p25, 0.5, 0.0)
    # symptoms logged within 6 h count as feeling off
    if len(data.symptoms):
        sy_utc = to_ns(data.symptoms["time"].sort_values())
        six_ns = int(pd.Timedelta(hours=6).value)
        recent = np.searchsorted(sy_utc, t_utc, side="left") - np.searchsorted(sy_utc, t_utc - six_ns, side="left")
        df["feeling_off"] = np.where(recent > 0, 2.0, df["feeling_off"])

    df["score"] = df[COMPONENTS].sum(axis=1)
    df["overnight"] = _in_sleep_window(hours, data.profile.sleep_window.start, data.profile.sleep_window.end)
    return df


def thresholds(data: EngineData, as_of: pd.Timestamp, trigger_rungs: dict[str, str] | None = None, days: int = 90) -> tuple[float, float, pd.DataFrame]:
    grid = pd.date_range(as_of - pd.Timedelta(days=days), as_of, freq="h", tz=data.tz)
    g = score_grid(data, grid, as_of=as_of, trigger_rungs=trigger_rungs)
    awake = g[~g["overnight"]]["score"]
    if len(awake) == 0:
        return 1.0, 2.0, g
    high = float(awake.quantile(1 - HIGH_SHARE)); medium = float(awake.quantile(1 - MEDIUM_SHARE))
    if high <= medium:
        high = medium + 0.5
    return medium, high, g


def _clock_words(h: int) -> str:
    """12-hour clock words for an hour: 0 -> midnight, 12 -> noon, 19 -> 7 pm."""
    h %= 24
    if h == 0:
        return "midnight"
    if h == 12:
        return "noon"
    return f"{h % 12} {'am' if h < 12 else 'pm'}"


def _pronouns(data: EngineData) -> tuple[str, str]:
    """(possessive, object): 'her'/'her' when a carer keeps the diary, 'your'/'you' when the person does."""
    role = getattr(data.profile, "role", None)
    role = str(role.value if hasattr(role, "value") else role)
    return ("her", "her") if role == "carer" else ("your", "you")


REASON_MAX_CHARS = 34
_COUNT_WORDS = {1: "One", 2: "Two"}


def _reason_text(component: str, pts: float, row: pd.Series, data: EngineData, hist: np.ndarray, n_hist: int) -> str:
    """Short third-person value for a key/value row (the UI supplies the key from `factor`). Keep under ~34 chars."""
    h = int(row["hour"])
    poss, obj = _pronouns(data)
    if component == "hour_band":
        if pts >= 2:
            text = f"{_clock_words(h)}–{_clock_words(h + HORIZON_HOURS)} is {poss} busiest stretch"
            return text if len(text) <= REASON_MAX_CHARS else f"{poss.capitalize()} busiest hours"
        if pts > 1.2:
            return f"A busier time of day for {obj}"
        if pts >= 0.8:
            return "An average time of day"
        return "A quieter time of day"
    if component == "today_count":
        n = int(row["today_count_n"]); return f"{_COUNT_WORDS.get(n, str(n))} already today"
    if component == "recent_gap":
        hrs = float(row["hours_since_last_n"])
        return f"Last one {max(1, round(hrs * 60))} min ago" if hrs < 1 else f"Last one {hrs:.1f} h ago"
    if component == "week_vs_baseline":
        n = int(row["last7_n"])
        return f"{n} in a week, above {poss} usual" if pts >= 1 else f"{n} in a week, a bit above usual"
    if component == "dose_overdue":
        return "A dose is overdue"
    if component == "dose_skipped":
        return "A dose was skipped today"
    if component == "feeling_off":
        return "Warning signs in the last 6 h"
    if component == "stress":
        return "High stress today"
    if component == "short_sleep":
        return "Short sleep last night"
    return component


def compute_risk(data: EngineData, at: pd.Timestamp | None = None, trigger_rungs: dict[str, str] | None = None) -> RiskNow:
    at = ensure_tz(at, data.tz) if at is not None else data.now()
    hist, n_hist = hour_histogram(data, at)
    learning = n_hist < LEARNING_MODE_MIN_EVENTS
    medium, high, _ = thresholds(data, at, trigger_rungs) if not learning else (1.0, 2.0, None)
    row = score_grid(data, pd.DatetimeIndex([at]), as_of=at, trigger_rungs=trigger_rungs).iloc[0]
    if learning:
        score = float(row["today_count"] + row["recent_gap"] + row["feeling_off"] + row["dose_skipped"])
    else:
        score = float(row["score"])
    tier = "high" if score >= high else ("medium" if score >= medium else "low")
    reasons = []
    for c in COMPONENTS:
        pts = float(row[c])
        if learning and c in ("hour_band", "week_vs_baseline", "stress", "short_sleep"):
            continue
        if pts > 0:
            reasons.append(RiskReason(factor=c, points=pts, text=_reason_text(c, pts, row, data, hist, n_hist)))
    reasons.sort(key=lambda r: -r.points)
    if not reasons:
        reasons.append(RiskReason(factor="quiet", points=0.0, text="Quiet so far today" if not learning else f"Still learning {_pronouns(data)[0]} pattern"))
    return RiskNow(
        tier=tier, score=round(score, 2), computed_at=at.to_pydatetime(), horizon_hours=3, reasons=reasons[:3],
        learning_mode=learning, overnight_no_data=bool(row["overnight"]),
        thresholds={"medium": round(medium, 2), "high": round(high, 2)}, disclaimer=DISCLAIMER,
    )
