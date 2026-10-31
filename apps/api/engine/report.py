"""Clinic report data: one page in the shape NICE NG217, the AAN quality measure and epilepsy nurses expect.
Counts first, per-28-day rates, date of last seizure per type, completeness line, risk factors as facts.
Wording rules are enforced here so no downstream template can break them."""
from __future__ import annotations

import pandas as pd

from contracts import ClinicReport, MedicationChange, TriggerTest, TypeCount
from .data import EngineData
from .stats import cluster_days, seizure_free_runs

ILAE_NAMES = {
    "aware": "focal aware", "staring": "absence or focal impaired awareness (staring)", "impaired_awareness": "focal impaired awareness",
    "convulsive": "focal to bilateral or generalised tonic-clonic", "drop": "atonic (drop)", "jerk": "myoclonic", "unsure": "unknown onset, possible seizure",
}
WORDING_NOTES = [
    "Seizure types use ILAE 2017 names; the person's own label is shown in brackets.",
    "Unwitnessed or uncertain events are listed as unknown onset, possible seizure.",
    "Rates are per 28 days; percentage change is against the prior window of the same length.",
    "Days without any entry are not seizure-free; see the completeness line.",
    "No seizure-free claim is made unless 12 months or three times the longest prior interval have passed.",
    "Facts are reported, not diagnostic labels: a seizure of 5 minutes or more is listed as such.",
]
CLUSTER_DEFINITION = "3 or more seizures in a calendar day, or more than the person's own 90th percentile day"


def build_clinic_report(data: EngineData, as_of: pd.Timestamp | None = None, window_days: int = 90, medication_changes: list[MedicationChange] | None = None, triggers: list[TriggerTest] | None = None, questions: list[str] | None = None, sudep_last_discussed=None) -> ClinicReport:
    as_of = as_of or data.now()
    end = as_of.tz_convert(data.tz)
    start = end - pd.Timedelta(days=window_days)
    pstart = start - pd.Timedelta(days=window_days)
    ev = data.events_between(start, end)
    prior = data.events_between(pstart, start)
    daily = data.daily_counts(start=start.tz_localize(None).normalize(), end=end.tz_localize(None).normalize())
    daily = daily.reindex(pd.date_range(start.tz_localize(None).normalize(), end.tz_localize(None).normalize(), freq="D"), fill_value=0)

    # completeness: a day counts as logged if it has an event, a dose or a check-in
    logged_days = set(daily[daily > 0].index)
    if len(data.doses):
        logged_days |= set(data.doses["scheduled_time"].dt.tz_localize(None).dt.normalize())
    if len(data.checkins):
        logged_days |= set(data.checkins["date"].dt.normalize())
    logged_days = {d for d in logged_days if daily.index.min() <= d <= daily.index.max()}
    by_logger = ev["who_logged"].value_counts().to_dict() if len(ev) else {}

    factor = 28 / window_days
    total = int(len(ev)); prior_total = int(len(prior))
    per28 = round(total * factor, 1); prior28 = round(prior_total * factor, 1)
    pct_change = round((per28 - prior28) / prior28 * 100, 1) if prior28 else None
    conv = data.events[data.events["type"] == "convulsive"]
    last_conv = conv["start_time"].max() if len(conv) else None
    last_by_type = {t: str(sub["start_time"].max().date()) for t, sub in ev.groupby("type")} if len(ev) else {}
    by_type: list[TypeCount] = []
    for t, sub in (ev.groupby("type") if len(ev) else []):
        labels = sub["original_label"].dropna()
        label = labels.mode().iloc[0] if len(labels) else None
        by_type.append(TypeCount(
            type=t, ilae_name=ILAE_NAMES.get(t, t), patient_label=label, count=int(len(sub)), per_28_days=round(len(sub) * factor, 1),
            prior_count=int((prior["type"] == t).sum()), median_duration_s=float(sub["duration_s"].dropna().median()) if sub["duration_s"].notna().any() else None,
            max_duration_s=float(sub["duration_s"].dropna().max()) if sub["duration_s"].notna().any() else None,
            pct_asleep=round(float(sub["asleep_at_onset"].dropna().astype(bool).mean() * 100), 1) if sub["asleep_at_onset"].notna().any() else None,
            pct_witnessed=round(float((sub["who_logged"] != "patient").mean() * 100), 1) if len(sub) else None,
            count_ge_5min=int((sub["duration_s"].fillna(0) >= 300).sum()), last_seen=sub["start_time"].max().date(),
        ))
    by_type.sort(key=lambda x: -x.count)
    # weekly by type
    weekly = []
    if len(ev):
        wk = ev.assign(week=ev["start_time"].dt.tz_localize(None).dt.to_period("W-MON").dt.start_time)
        for w, sub in wk.groupby("week"):
            weekly.append({"week_start": w.date(), "counts": sub["type"].value_counts().to_dict()})
    # medication
    current = [{"drug": m.drug, "dose_mg": m.dose_mg, "times": list(m.times or [])} for m in data.profile.medications if not m.as_needed]
    doses = data.doses[(data.doses["scheduled_time"] >= start) & (data.doses["scheduled_time"] < end)] if len(data.doses) else data.doses
    missed = int(doses["skipped"].sum()) if len(doses) else 0
    adherence = round(float(doses["taken_time"].notna().mean() * 100), 1) if len(doses) else None
    rescue = []
    all_daily = data.daily_counts()
    for _, r in ev[ev["rescue_drug"].notna()].iterrows():
        d = r["start_time"].tz_localize(None).normalize()
        rescue.append({"date": d.date(), "drug": str(r["rescue_drug"]), "dose_mg": r["rescue_dose_mg"], "seizures_that_day": int(all_daily.get(d, 0)), "seizures_next_3_days": int(all_daily[(all_daily.index > d) & (all_daily.index <= d + pd.Timedelta(days=3))].sum())})
    # wellbeing
    ci = data.checkins[(data.checkins["date"] >= start.tz_localize(None)) & (data.checkins["date"] <= end.tz_localize(None))] if len(data.checkins) else data.checkins
    sleep_h = ((ci["sleep_wake_time"] - ci["sleep_bed_time"]).dt.total_seconds() / 3600).dropna() if len(ci) else pd.Series(dtype=float)
    wellbeing = {
        "mean_stress": round(float(ci["stress"].dropna().mean()), 1) if len(ci) and ci["stress"].notna().any() else None,
        "mean_fatigue": round(float(ci["fatigue"].dropna().mean()), 1) if len(ci) and ci["fatigue"].notna().any() else None,
        "mean_sleep_hours": round(float(sleep_h.mean()), 1) if len(sleep_h) else None,
        "laep_total": None, "nddie_total": None, "nddie_item4_flag": None, "gad7_total": None,
    }
    # risk factors as facts
    nocturnal_30 = data.events_between(end - pd.Timedelta(days=30), end)
    nocturnal_30 = int(nocturnal_30["asleep_at_onset"].fillna(False).astype(bool).sum() + ((nocturnal_30["asleep_at_onset"].isna()) & (nocturnal_30["start_time"].dt.hour < 6)).sum())
    conv_12m = int(len(data.events_between(end - pd.Timedelta(days=365), end).query("type == 'convulsive'")))
    alcohol = bool(len(ci) and (ci["alcohol_units"].fillna(0) >= 3).any())
    risk_factors = [
        {"factor": "Tonic-clonic seizures in window", "present": bool((ev["type"] == "convulsive").any()) if len(ev) else False, "detail": f"{int((ev['type'] == 'convulsive').sum()) if len(ev) else 0} in window; {conv_12m} in the last 12 months"},
        {"factor": "Seizures during sleep", "present": nocturnal_30 > 0, "detail": f"{nocturnal_30} in the last 30 days (logged as asleep, or before 06:00)"},
        {"factor": "Sleeps alone or unsupervised", "present": data.profile.sleeps_alone, "detail": "from profile" if data.profile.sleeps_alone is not None else "not recorded"},
        {"factor": "Missed doses", "present": missed > 0 if len(doses) else None, "detail": f"{missed} skipped of {len(doses)} scheduled" if len(doses) else "dose logging not in use"},
        {"factor": "Alcohol", "present": alcohol if len(ci) else None, "detail": "3+ units on at least one day" if alcohol else ("none logged" if len(ci) else "not recorded")},
        {"factor": "Frequency up more than 25% vs prior window", "present": (pct_change is not None and pct_change > 25), "detail": f"{per28} vs {prior28} per 28 days" if prior28 else "no prior window"},
    ]
    p90 = float(all_daily[(all_daily.index >= daily.index.min() - pd.Timedelta(days=90)) & (all_daily.index <= daily.index.max())].quantile(0.9)) if len(all_daily) else None
    completeness_pct = round(len(logged_days) / len(daily) * 100) if len(daily) else 0
    effort = f"{len(logged_days)} of {len(daily)} days have at least one entry ({completeness_pct}%). Days without entries are not seizure-free."
    if len(ev) and (ev["confidence"] == "guess").mean() > 0.1:
        effort += f" {int((ev['confidence'] == 'guess').sum())} events are marked as guesses."
    return ClinicReport(
        generated_at=end.to_pydatetime(), window_start=start.date(), window_end=end.date(), prior_window_start=pstart.date(), prior_window_end=start.date(),
        completeness={"days_with_any_entry": len(logged_days), "days_in_window": int(len(daily)), "pct_events_logged_within_24h": None, "logged_by": {str(k): int(v) for k, v in by_logger.items()}},
        headline={
            "total": total, "per_28_days": per28, "prior_per_28_days": prior28, "pct_change": pct_change, "seizure_days": int((daily > 0).sum()),
            "days_since_last_convulsive": int((end - last_conv).days) if last_conv is not None else None,
            "longest_seizure_free_run_days": seizure_free_runs(daily), "last_seizure_by_type": last_by_type,
        },
        by_type=by_type, cluster_definition=CLUSTER_DEFINITION, cluster_days=cluster_days(daily, "3 in 24 h", p90),
        events_ge_5min=int((ev["duration_s"].fillna(0) >= 300).sum()) if len(ev) else 0, nocturnal_count_30d=nocturnal_30, convulsive_count_12m=conv_12m,
        weekly_by_type=weekly,
        medication={"current": current, "changes": medication_changes or [], "adherence_pct": adherence, "missed_doses": missed, "rescue_uses": rescue},
        wellbeing=wellbeing, risk_factors=risk_factors,
        triggers=[t for t in (triggers or []) if t.rung in ("supported", "emerging")],
        questions_for_clinician=questions or [], sudep_last_discussed=sudep_last_discussed, logging_effort_note=effort, wording_notes=WORDING_NOTES,
    )
