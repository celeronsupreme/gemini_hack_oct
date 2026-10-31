import pandas as pd
from engine import compute_risk, backtest, hourly_stats, baseline_stats, adjust_bh, build_clinic_report
from engine import test_trigger as run_trigger_test
from contracts import TriggerDefinition, SeizureEvent


def test_import_counts(diary):
    assert len(diary) == 2598
    assert sum(e.severity == "severe" for e in diary) == 791
    assert all(e.start_time.tzinfo is not None for e in diary)
    assert not any("Seema" in (e.notes or "") for e in diary), "names must be redacted on import"


def test_hourly_profile_matches_brief(data):
    h = hourly_stats(data, as_of=pd.Timestamp("2026-08-24 23:59", tz=data.tz), window_days=3000)
    assert h.peak_hour == 19
    assert 70 <= h.share_12_22_pct <= 80


def test_risk_now_shapes(data):
    r = compute_risk(data, pd.Timestamp("2026-08-21 18:30", tz=data.tz))
    assert r.tier in ("low", "medium", "high") and r.horizon_hours == 3 and 1 <= len(r.reasons) <= 3
    assert r.thresholds.high > r.thresholds.medium
    night = compute_risk(data, pd.Timestamp("2026-08-21 03:00", tz=data.tz))
    assert night.overnight_no_data is True


def test_learning_mode_under_30_events(diary):
    from engine import EngineData, default_profile
    small = EngineData.from_models(diary[:20], profile=default_profile())
    r = compute_risk(small, diary[19].start_time)
    assert r.learning_mode is True


def test_backtest_reproduces_brief(data):
    bt = backtest(data, "2024-01-01", "2026-08-24")
    assert bt["auc"] >= 0.65, bt
    assert bt["high_over_low"] >= 2.5, bt
    assert 10 <= bt["tiers"]["high"]["hours_pct"] <= 25, bt


def test_baseline_verdict(data):
    b = baseline_stats(data, as_of=pd.Timestamp("2025-03-12", tz=data.tz))
    assert "range" in b.this_week_verdict


def test_trigger_ladder_never_rejects_for_lack_of_data(data):
    t = run_trigger_test(data, TriggerDefinition(id="x", name="swimming", kind="daily_factor"))
    assert t.rung == "watching" and t.units_to_next_verdict == 10
    tests = adjust_bh([run_trigger_test(data, TriggerDefinition(id="s", name="hot shower or bath", kind="exposure", context_tag="shower_bath")),
                       run_trigger_test(data, TriggerDefinition(id="sc", name="screens", kind="exposure", context_tag="screen"))])
    shower = next(x for x in tests if x.trigger_id == "s")
    assert shower.rung == "emerging" and shower.ratio and shower.ratio > 1.3
    assert shower.method.startswith("notes only"), "imported tags have no denominator and must be capped at emerging"
    assert all(x.tests_corrected_for == 2 for x in tests if x.p_value is not None)


def test_clinic_report_wording_rules(data):
    rep = build_clinic_report(data, as_of=pd.Timestamp("2026-08-24 23:59", tz=data.tz))
    assert rep.completeness.days_in_window == 91
    assert "not seizure-free" in rep.logging_effort_note
    assert all(b.ilae_name for b in rep.by_type)
    assert rep.cluster_definition
