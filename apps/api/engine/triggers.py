"""Trigger lab: test any suspected trigger or warning sign on the person's own history and place it on a
five-rung ladder. Lack of data is never a verdict.

Modes
- daily_factor: a check-in field (stress >= 7, unwell, period_started, a daily_trigger_flags entry). Exposed days vs
  unexposed days among days with a check-in; rate = seizures per day.
- exposure: timed exposures (walks from a watch, showers logged by voice). Seizures in the window after each exposure
  vs the rate in the same clock hours on days without that exposure.
- symptom: a logged warning symptom; same as exposure with a short window.
- tag_only (fallback): the tag exists only on seizure rows (imported diaries). Severe share with the tag vs without.
  No denominator, so the rung is capped at "emerging" and the method says so.
"""
from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd

from contracts import TriggerDefinition, TriggerTest
from .data import EngineData, to_ns

MIN_UNITS_VERDICT = 10
MIN_UNITS_NEGATIVE = 20
MIN_UNITS_UNLIKELY = 30
PERMUTATIONS = 1000
BANDS = [(0, 8), (8, 12), (12, 17), (17, 24)]

CHECKIN_FIELD_RULES = {
    "stress": lambda s: s >= 7, "fatigue": lambda s: s >= 7, "mood": lambda s: s <= 3, "sleep_quality": lambda s: s <= 2,
    "unwell": lambda s: bool(s), "period_started": lambda s: bool(s), "feeling_off": lambda s: bool(s), "exercise": lambda s: bool(s),
    "big_event_tomorrow": lambda s: bool(s), "alcohol_units": lambda s: s >= 3,
}


def _band(h: int) -> int:
    for i, (a, b) in enumerate(BANDS):
        if a <= h < b:
            return i
    return len(BANDS) - 1


def _rate_ratio_ci(k1: int, n1: float, k2: int, n2: float) -> tuple[float | None, float | None, float | None]:
    """Rate ratio with an approximate 95% CI (log-normal, Poisson counts)."""
    if n1 <= 0 or n2 <= 0 or k2 == 0 and k1 == 0:
        return None, None, None
    r1 = k1 / n1; r2 = k2 / n2
    if r2 == 0:
        return None, None, None
    ratio = r1 / r2
    if k1 == 0:
        return ratio, 0.0, None
    se = math.sqrt(1 / k1 + 1 / max(k2, 1))
    return ratio, ratio * math.exp(-1.96 * se), ratio * math.exp(1.96 * se)


def _rung(units: int, ratio: float | None, ci_high: float | None, p_adj: float | None, literature_prior: bool, cap_emerging: bool, confounded: bool) -> tuple[str, int | None]:
    thr = 1.2 if literature_prior else 1.3
    if units < MIN_UNITS_VERDICT or ratio is None:
        return "watching", MIN_UNITS_VERDICT - units if units < MIN_UNITS_VERDICT else None
    if ratio >= thr:
        if p_adj is not None and p_adj < 0.05 and not confounded and not cap_emerging:
            return "supported", None
        return "emerging", None
    if units >= MIN_UNITS_UNLIKELY and (ratio < 0.8 or (ci_high is not None and ci_high < 1.2)) and not cap_emerging:
        return "unlikely", None
    if units >= MIN_UNITS_NEGATIVE:
        return "not_seen_so_far", None
    return "watching", MIN_UNITS_NEGATIVE - units


def _texts(name: str, kind: str, rung: str, ratio: float | None, units: int, k1: int, window_h: float, units_to_next: int | None, cap: bool, confounded: bool, ratio_bands: float | None) -> tuple[str, str]:
    unit_word = "days" if kind == "daily_factor" else ("times logged" if kind == "symptom" else "exposures")
    horizon = "that day" if kind == "daily_factor" else f"within {window_h:g} h"
    r = f"{ratio:.1f}×" if ratio is not None else "no comparison yet"
    if rung == "watching":
        if units >= MIN_UNITS_VERDICT and ratio is not None:
            return (f"No sign of an effect yet ({r} {horizon} across {units} {unit_word}), but {units_to_next or 10} more {unit_word} are needed before that means anything.", f"Keep logging {name}; I will ask about it at check-in.")
        more = f" {units_to_next} more {unit_word} and I can start comparing." if units_to_next else ""
        return (f"Logged. {units} {unit_word} so far; not enough to compare yet.{more}", f"Keep logging {name}; I will ask about it at check-in.")
    if cap:
        # notes-only mode: the comparison is severe share among seizures with the note vs without
        pct = f"{(k1 / units * 100):.0f}%" if units else "0%"
        if rung == "emerging":
            return (f"Of {units} seizures whose notes mention {name}, {pct} were severe, {r} the rate for your other seizures. This comes from seizure notes only, so there is no comparison with days it did not happen; treat it as a lead.", "Log it at check-in on ordinary days too, so it can be tested properly.")
        return (f"Of {units} seizures whose notes mention {name}, {pct} were severe, {r} your other seizures: no difference so far.", "Log it at check-in on ordinary days too, so it can be tested properly.")
    if rung == "emerging":
        extra = " This comes from seizure notes only, so there is no proper comparison day; treat it as a lead." if cap else ""
        extra += f" Allowing for time of day it is {ratio_bands:.1f}×." if (confounded and ratio_bands is not None) else ""
        return (f"Seizures are {r} more common {horizon} after {name} so far, from {units} {unit_word} ({k1} seizures). Not proven yet.{extra}", "Keep logging; a verdict needs more data and a steady effect.")
    if rung == "supported":
        return (f"In your log, {name} is followed by more seizures: {r} {horizon}, across {units} {unit_word} ({k1} seizures).", "Worth discussing with your nurse; add to the clinic report.")
    if rung == "not_seen_so_far":
        return (f"No difference in your log yet: {r} {horizon} across {units} {unit_word}. It might still matter on some days; I will keep watching.", "Keep logging or leave it; it stays open.")
    return (f"Your log points the other way: {r} {horizon} across {units} {unit_word}.", "You can archive this or keep logging it; it re-opens if the pattern changes.")


def _count_in_windows(ev_utc: np.ndarray, starts_utc: np.ndarray, window_ns: int) -> int:
    a = np.searchsorted(ev_utc, starts_utc, side="left"); b = np.searchsorted(ev_utc, starts_utc + window_ns, side="left")
    return int((b - a).sum())


def _timed_exposure_test(data: EngineData, name: str, windows_start: pd.DatetimeIndex, window_h: float, kind: str) -> dict:
    ev = data.events
    ev_utc = to_ns(ev["start_time"]) if len(ev) else np.array([], dtype="int64")
    ws_local = windows_start.tz_convert(data.tz)
    ws_utc = to_ns(ws_local)
    window_ns = int(pd.Timedelta(hours=window_h).value)
    k1 = _count_in_windows(ev_utc, ws_utc, window_ns)
    n1_hours = len(ws_utc) * window_h
    # baseline: same clock hours on days without exposure
    exp_days = set(ws_local.normalize().tz_localize(None))
    all_days = pd.date_range(ev["start_time"].min().tz_localize(None).normalize(), ev["start_time"].max().tz_localize(None).normalize(), freq="D") if len(ev) else pd.DatetimeIndex([])
    free_days = [d for d in all_days if d not in exp_days]
    hours_profile = ws_local.hour.to_numpy()
    base_starts = []
    rng = np.random.default_rng(7)
    sample_days = rng.choice(len(free_days), size=min(len(free_days), max(200, len(ws_local))), replace=False) if len(free_days) else []
    for i in sample_days:
        d = free_days[i]
        for h in np.unique(hours_profile):
            base_starts.append(pd.Timestamp(d).tz_localize(data.tz, ambiguous=True, nonexistent="shift_forward") + pd.Timedelta(hours=int(h)))
    if base_starts:
        bs = to_ns(base_starts)
        k2 = _count_in_windows(ev_utc, bs, window_ns); n2_hours = len(bs) * window_h
    else:
        k2, n2_hours = 0, 0.0
    ratio, lo, hi = _rate_ratio_ci(k1, n1_hours, k2, n2_hours)
    # permutation: move each exposure to a random day (same clock time), 1000 times
    p = None
    if len(ws_local) and len(all_days) > 30:
        day_ns = to_ns(pd.DatetimeIndex(all_days).tz_localize(data.tz, ambiguous=True, nonexistent="shift_forward"))
        offs = (ws_utc - to_ns(ws_local.normalize()))
        ge = 0
        for _ in range(PERMUTATIONS):
            pick = day_ns[rng.integers(len(day_ns), size=len(offs))] + offs
            if _count_in_windows(ev_utc, pick, window_ns) >= k1:
                ge += 1
        p = (ge + 1) / (PERMUTATIONS + 1)
    # within-band ratio (stratified by time of day)
    ratio_bands = None
    try:
        bands_ws = np.array([_band(h) for h in hours_profile])
        num = den = 0.0
        for bi in range(len(BANDS)):
            sel = bands_ws == bi
            if not sel.any():
                continue
            k1b = _count_in_windows(ev_utc, ws_utc[sel], window_ns); n1b = sel.sum() * window_h
            hb = np.unique(hours_profile[sel])
            bsb = [pd.Timestamp(free_days[i]).tz_localize(data.tz, ambiguous=True, nonexistent="shift_forward") + pd.Timedelta(hours=int(h)) for i in sample_days for h in hb]
            if not bsb:
                continue
            bsb_utc = to_ns(bsb)
            k2b = _count_in_windows(ev_utc, bsb_utc, window_ns); n2b = len(bsb_utc) * window_h
            if n2b and k2b:
                w = sel.sum()
                num += w * (k1b / n1b) / (k2b / n2b); den += w
        ratio_bands = num / den if den else None
    except Exception:
        ratio_bands = None
    return dict(units=len(ws_local), unexposed_units=len(base_starts), k1=k1, k2=k2, rate1=k1 / n1_hours if n1_hours else 0.0, rate2=k2 / n2_hours if n2_hours else 0.0, ratio=ratio, ci_low=lo, ci_high=hi, p=p, ratio_bands=ratio_bands, method=f"{kind}: seizures within {window_h:g} h after each exposure vs the same clock hours on days without it; permutation test ({PERMUTATIONS} shuffles) moving exposures to random days; time-of-day stratified ratio as confounder check")


def _daily_factor_test(data: EngineData, defn: TriggerDefinition) -> dict:
    ci = data.checkins
    if len(ci) == 0:
        return dict(units=0, unexposed_units=0, k1=0, k2=0, rate1=0.0, rate2=0.0, ratio=None, ci_low=None, ci_high=None, p=None, ratio_bands=None, method="daily factor: no check-ins yet")
    field = defn.checkin_field or defn.name
    if field in CHECKIN_FIELD_RULES and field in ci.columns:
        vals = ci[field]
        exposed = vals.apply(lambda v: CHECKIN_FIELD_RULES[field](v) if pd.notna(v) else None)
    else:
        exposed = ci["daily_trigger_flags"].apply(lambda m: m.get(defn.name) if isinstance(m, dict) and defn.name in m else None)
    mask = exposed.notna()
    days = ci.loc[mask, "date"].dt.normalize(); lab = exposed[mask].astype(bool).to_numpy()
    daily = data.daily_counts()
    counts = daily.reindex(days, fill_value=0).to_numpy()
    k1 = int(counts[lab].sum()); n1 = int(lab.sum()); k2 = int(counts[~lab].sum()); n2 = int((~lab).sum())
    ratio, lo, hi = _rate_ratio_ci(k1, n1, k2, n2)
    p = None
    if n1 >= MIN_UNITS_VERDICT and n2 >= 5:
        rng = np.random.default_rng(11); ge = 0
        for _ in range(PERMUTATIONS):
            perm = rng.permutation(lab)
            if counts[perm].sum() >= k1:
                ge += 1
        p = (ge + 1) / (PERMUTATIONS + 1)
    return dict(units=n1, unexposed_units=n2, k1=k1, k2=k2, rate1=k1 / n1 if n1 else 0.0, rate2=k2 / n2 if n2 else 0.0, ratio=ratio, ci_low=lo, ci_high=hi, p=p, ratio_bands=None, method=f"daily factor: seizures per day on days with {defn.name} vs days with a check-in and without it; permutation test ({PERMUTATIONS} shuffles)")


def _tag_only_test(data: EngineData, tag: str) -> dict:
    ev = data.events
    has = ev["context_tags"].apply(lambda t: tag in (t or []))
    n1 = int(has.sum()); n2 = int((~has).sum())
    k1 = int((ev.loc[has, "severity"] == "severe").sum()); k2 = int((ev.loc[~has, "severity"] == "severe").sum())
    ratio, lo, hi = _rate_ratio_ci(k1, n1, k2, n2)
    p = None
    if n1 >= MIN_UNITS_VERDICT:
        rng = np.random.default_rng(5); sev = (ev["severity"] == "severe").to_numpy(); ge = 0
        for _ in range(PERMUTATIONS):
            pick = rng.choice(len(sev), size=n1, replace=False)
            if sev[pick].sum() >= k1:
                ge += 1
        p = (ge + 1) / (PERMUTATIONS + 1)
    return dict(units=n1, unexposed_units=n2, k1=k1, k2=k2, rate1=k1 / n1 if n1 else 0.0, rate2=k2 / n2 if n2 else 0.0, ratio=ratio, ci_low=lo, ci_high=hi, p=p, ratio_bands=None, method="notes only: share of severe seizures among seizures whose note mentions this vs the rest; no seizure-free comparison exists, so the rung is capped at emerging")


def test_trigger(data: EngineData, defn: TriggerDefinition, as_of: pd.Timestamp | None = None, history: list[dict] | None = None) -> TriggerTest:
    as_of = as_of or data.now()
    kind = str(defn.kind.value if hasattr(defn.kind, "value") else defn.kind)
    tag = str(defn.context_tag.value if defn.context_tag is not None and hasattr(defn.context_tag, "value") else defn.context_tag) if defn.context_tag is not None else None
    cap = False
    if kind == "daily_factor":
        res = _daily_factor_test(data, defn)
    elif kind == "symptom":
        sy = data.symptoms
        starts = pd.DatetimeIndex(sy[sy["text"].str.lower().str.contains(defn.name.lower()) | (sy["text"].str.len() > 0)]["time"]) if len(sy) else pd.DatetimeIndex([])
        res = _timed_exposure_test(data, defn.name, starts, defn.window_hours or 6, "symptom") if len(starts) else dict(units=0, unexposed_units=0, k1=0, k2=0, rate1=0.0, rate2=0.0, ratio=None, ci_low=None, ci_high=None, p=None, ratio_bands=None, method="symptom: no symptom entries yet")
    else:
        ex = data.exposures
        sel = ex[(ex["name"].str.lower() == defn.name.lower()) | (ex["name"].str.lower() == (tag or "").lower())] if len(ex) else ex
        if len(sel):
            res = _timed_exposure_test(data, defn.name, pd.DatetimeIndex(sel["end"]), defn.window_hours or 6, "exposure")
        elif tag:
            res = _tag_only_test(data, tag); cap = True
        else:
            res = dict(units=0, unexposed_units=0, k1=0, k2=0, rate1=0.0, rate2=0.0, ratio=None, ci_low=None, ci_high=None, p=None, ratio_bands=None, method="exposure: nothing logged yet")
    confounded = res["ratio_bands"] is not None and res["ratio"] is not None and res["ratio_bands"] < res["ratio"] * (2 / 3)
    rung, to_next = _rung(res["units"], res["ratio"], res["ci_high"], res["p"], bool(defn.literature_prior), cap, confounded)
    plain, nxt = _texts(defn.name, kind, rung, res["ratio"], res["units"], res["k1"], defn.window_hours or 6, to_next, cap, confounded, res["ratio_bands"])
    note = None
    if confounded:
        note = f"{defn.name} mostly happens in your riskier hours; after allowing for time of day the ratio is {res['ratio_bands']:.1f}×."
    elif cap:
        note = "From seizure notes only: no days without the trigger are recorded, so this cannot rise above emerging until daily check-ins exist."
    hist = list(history or [])
    if not hist or hist[-1]["rung"] != rung:
        hist.append({"at": as_of.to_pydatetime(), "rung": rung})
    return TriggerTest(
        trigger_id=defn.id or defn.name, trigger=defn.name, kind=kind, rung=rung,
        exposure_units=int(res["units"]), unexposed_units=int(res["unexposed_units"]), seizures_exposed=int(res["k1"]), seizures_unexposed=int(res["k2"]),
        rate_exposed=round(float(res["rate1"]), 4), rate_unexposed=round(float(res["rate2"]), 4),
        ratio=round(res["ratio"], 2) if res["ratio"] is not None else None, ci_low=round(res["ci_low"], 2) if res["ci_low"] is not None else None, ci_high=round(res["ci_high"], 2) if res["ci_high"] is not None else None,
        p_value=round(res["p"], 4) if res["p"] is not None else None, p_adjusted=round(res["p"], 4) if res["p"] is not None else None, tests_corrected_for=1,
        confounder_note=note, ratio_within_time_bands=round(res["ratio_bands"], 2) if res["ratio_bands"] is not None else None,
        units_to_next_verdict=to_next, next_step=nxt, plain_text=plain, method=res["method"], computed_at=as_of.to_pydatetime(), history=hist,
    )


def adjust_bh(tests: list[TriggerTest], defs: dict[str, TriggerDefinition] | None = None) -> list[TriggerTest]:
    """Benjamini–Hochberg across every test with a p-value; re-derives rungs with the adjusted p."""
    with_p = [t for t in tests if t.p_value is not None]
    m = len(with_p)
    if m == 0:
        return tests
    order = sorted(with_p, key=lambda t: t.p_value)
    adj = {}
    prev = 1.0
    for rank, t in reversed(list(enumerate(order, start=1))):
        val = min(prev, t.p_value * m / rank); prev = val
        adj[t.trigger_id] = min(val, 1.0)
    out = []
    for t in tests:
        if t.trigger_id in adj:
            cap = t.method.startswith("notes only")
            confounded = t.ratio_within_time_bands is not None and t.ratio is not None and t.ratio_within_time_bands < t.ratio * (2 / 3)
            prior = bool(defs[t.trigger_id].literature_prior) if defs and t.trigger_id in defs else False
            rung, to_next = _rung(t.exposure_units, t.ratio, t.ci_high, adj[t.trigger_id], prior, cap, confounded)
            plain, nxt = _texts(t.trigger, str(t.kind.value if hasattr(t.kind, "value") else t.kind), rung, t.ratio, t.exposure_units, t.seizures_exposed, 6, to_next, cap, confounded, t.ratio_within_time_bands)
            t = TriggerTest.model_validate({**t.model_dump(), "p_adjusted": round(adj[t.trigger_id], 4), "tests_corrected_for": m, "rung": rung, "plain_text": plain, "next_step": nxt, "units_to_next_verdict": to_next})
        out.append(t)
    return out
