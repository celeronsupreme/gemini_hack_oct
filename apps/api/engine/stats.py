"""Descriptive statistics the app shows: hour-of-day profile, monthly series, personal baseline,
and the before/after effect of each medication change."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

from contracts import HourlyStats, MonthlyStats, BaselineStats, MedicationChange
from .data import EngineData

LEARNING_MODE_MIN_EVENTS = 30


def hourly_stats(data: EngineData, window_days: int = 365, as_of: pd.Timestamp | None = None) -> HourlyStats:
    as_of = as_of or data.now()
    start = as_of - pd.Timedelta(days=window_days)
    ev = data.events_between(start, as_of)
    hours = ev["start_time"].dt.hour
    all_counts = hours.value_counts().reindex(range(24), fill_value=0)
    sev_counts = ev[ev["severity"] == "severe"]["start_time"].dt.hour.value_counts().reindex(range(24), fill_value=0)
    total = int(all_counts.sum())
    by_hour = []
    for h in range(24):
        share = all_counts[h] / total * 100 if total else 0.0
        by_hour.append({"hour": h, "all": int(all_counts[h]), "severe": int(sev_counts[h]), "share_pct": round(float(share), 2), "vs_flat": round(float(share / (100 / 24)), 2) if total else 0.0})
    dose_times = sorted({t for m in data.profile.medications for t in (m.times or [])})
    return HourlyStats(
        window_start=start.date(), window_end=as_of.date(), total=total, by_hour=by_hour,
        peak_hour=int(all_counts.idxmax()) if total else None,
        share_12_22_pct=round(float(all_counts[12:22].sum() / total * 100), 1) if total else 0.0,
        share_00_08_pct=round(float(all_counts[0:8].sum() / total * 100), 1) if total else 0.0,
        scheduled_dose_times=dose_times,
    )


def monthly_stats(data: EngineData, medication_changes: list[MedicationChange] | None = None) -> MonthlyStats:
    ev = data.events
    months = []
    if len(ev):
        local = ev["start_time"].dt.tz_localize(None)
        g = ev.assign(month=local.dt.to_period("M"), day=local.dt.normalize())
        for m, sub in g.groupby("month"):
            months.append({
                "month": str(m), "all": int(len(sub)), "severe": int((sub["severity"] == "severe").sum()),
                "days_with_seizure": int(sub["day"].nunique()),
                "median_duration_s": float(sub["duration_s"].dropna().median()) if sub["duration_s"].notna().any() else None,
            })
    return MonthlyStats(months=months, medication_changes=medication_changes or [])


def baseline_stats(data: EngineData, as_of: pd.Timestamp | None = None, window_days: int = 90) -> BaselineStats:
    as_of = as_of or data.now()
    end_day = as_of.tz_localize(None).normalize()
    start_day = end_day - pd.Timedelta(days=window_days)
    daily = data.daily_counts(start=start_day, end=end_day)
    daily = daily.reindex(pd.date_range(start_day, end_day, freq="D"), fill_value=0)
    severe = data.daily_counts(start=start_day, end=end_day, severe_only=True).reindex(daily.index, fill_value=0)
    weekly = daily.rolling(7).sum().dropna()
    this_week = float(daily.iloc[-7:].sum())
    events_in_window = int(daily.sum())
    if len(weekly) == 0:
        weekly = pd.Series([this_week])
    p25, med, p75, p90 = (float(weekly.quantile(q)) for q in (0.25, 0.5, 0.75, 0.9))
    if events_in_window < LEARNING_MODE_MIN_EVENTS:
        verdict = "Still learning your usual range"
    elif this_week > p90:
        verdict = "Well above your usual range"
    elif this_week > p75:
        verdict = "Above your usual range"
    elif this_week < p25:
        verdict = "Below your usual range"
    else:
        verdict = "Within your usual range"
    return BaselineStats(
        as_of=end_day.date(), window_days=window_days, per_day_mean=round(float(daily.mean()), 3), per_week_mean=round(float(daily.mean() * 7), 2),
        weekly_p25=round(p25, 1), weekly_median=round(med, 1), weekly_p75=round(p75, 1), weekly_p90=round(p90, 1),
        daily_p90=round(float(daily.quantile(0.9)), 1), this_week=this_week, this_week_verdict=verdict,
        severe_per_week_mean=round(float(severe.mean() * 7), 2), pct_days_with_seizure=round(float((daily > 0).mean() * 100), 1),
        events_in_window=events_in_window, learning_mode=events_in_window < LEARNING_MODE_MIN_EVENTS,
    )


def medication_change_effect(data: EngineData, change_date: pd.Timestamp, window_days: int = 56) -> dict:
    """Rate before vs after a change, Poisson test, and a plain verdict that respects the person's own spread."""
    d = pd.Timestamp(change_date).tz_localize(None).normalize()
    daily = data.daily_counts()
    pre = daily[(daily.index >= d - pd.Timedelta(days=window_days)) & (daily.index < d)]
    post = daily[(daily.index >= d) & (daily.index < d + pd.Timedelta(days=window_days))]
    severe = data.daily_counts(severe_only=True).reindex(daily.index, fill_value=0)
    out = {"before_per_week": None, "after_per_week": None, "before_severe_per_week": None, "after_severe_per_week": None, "p_value": None, "window_days": window_days, "verdict": "too early to tell"}
    if len(pre) < 14 or len(post) < 14:
        return out
    try:
        p = float(sstats.poisson_means_test(int(pre.sum()), len(pre), int(post.sum()), len(post)).pvalue)
    except Exception:
        p = None
    out.update({
        "before_per_week": round(float(pre.mean() * 7), 2), "after_per_week": round(float(post.mean() * 7), 2),
        "before_severe_per_week": round(float(severe[pre.index].mean() * 7), 2), "after_severe_per_week": round(float(severe[post.index].mean() * 7), 2),
        "p_value": round(p, 4) if p is not None else None,
    })
    # verdict against the person's own weekly spread in the year before the change
    year_before = daily[(daily.index >= d - pd.Timedelta(days=365)) & (daily.index < d)]
    weekly = year_before.rolling(7).sum().dropna()
    if len(post) < window_days:
        out["verdict"] = "too early to tell"
    elif p is not None and p < 0.01 and post.mean() > pre.mean() * 1.3:
        out["verdict"] = "clear rise"
    elif p is not None and p < 0.01 and post.mean() < pre.mean() * 0.77:
        out["verdict"] = "clear fall"
    elif p is not None and p < 0.05 and post.mean() > pre.mean() * 1.3:
        out["verdict"] = "probable rise"
    elif p is not None and p < 0.05 and post.mean() < pre.mean() * 0.77:
        out["verdict"] = "probable fall"
    elif len(weekly) and (weekly.quantile(0.1) <= post.mean() * 7 <= weekly.quantile(0.9)):
        out["verdict"] = "within usual range"
    else:
        out["verdict"] = "no clear change"
    return out


def medication_changes_with_effects(data: EngineData, timeline: pd.DataFrame) -> list[MedicationChange]:
    """`timeline` columns: date, drug, action, detail."""
    out = []
    for _, r in timeline.sort_values("date").iterrows():
        eff = medication_change_effect(data, pd.Timestamp(r["date"]))
        out.append(MedicationChange(date=pd.Timestamp(r["date"]).date(), drug=str(r["drug"]), action=str(r["action"]), detail=str(r["detail"]), **eff))
    return out


def cluster_days(daily: pd.Series, definition: str = "3 in 24 h", personal_p90: float | None = None) -> int:
    if definition.startswith("3"):
        n = int((daily >= 3).sum())
    else:
        n = int((daily >= 2).sum())
    if personal_p90 is not None:
        n = max(n, int((daily > personal_p90).sum()))
    return n


def seizure_free_runs(daily: pd.Series) -> int:
    best = run = 0
    for v in daily.values:
        run = run + 1 if v == 0 else 0
        best = max(best, run)
    return int(best)
