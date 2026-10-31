"""The service layer: loads EngineData from the store (cached by data version), runs the engine, saves results.
Routers call this; nothing here knows about HTTP."""
from __future__ import annotations

import threading
from datetime import datetime, timezone

import pandas as pd

from contracts import BaselineStats, ClinicReport, HourlyStats, MonthlyStats, RiskNow, TriggerDefinition, TriggerTest
from engine import EngineData, adjust_bh, baseline_stats, build_clinic_report, compute_risk, ensure_tz, hourly_stats, monthly_stats, test_trigger
from . import store
from .config import settings

_lock = threading.Lock()
_cache: dict[str, object] = {"version": None, "data": None}


def engine_data() -> EngineData:
    v = store.data_version()
    with _lock:
        if _cache["version"] != v or _cache["data"] is None:
            _cache["data"] = store.load_engine_data(); _cache["version"] = v
        return _cache["data"]  # type: ignore[return-value]


def invalidate() -> None:
    with _lock:
        _cache["version"] = None


def _at(at: str | None, data: EngineData) -> pd.Timestamp:
    return ensure_tz(at, data.tz) if at else data.now()


def trigger_rungs() -> dict[str, str]:
    defs = {d.id: d for d in store.list_trigger_definitions()}
    out = {}
    for t in store.list_trigger_tests():
        d = defs.get(t.trigger_id)
        key = (d.checkin_field or d.name).lower() if d else t.trigger.lower()
        out[key] = str(t.rung.value if hasattr(t.rung, "value") else t.rung)
    return out


def risk_now(at: str | None = None) -> RiskNow:
    data = engine_data()
    return compute_risk(data, _at(at, data), trigger_rungs=trigger_rungs())


def hourly(at: str | None = None, window_days: int = 365) -> HourlyStats:
    data = engine_data()
    return hourly_stats(data, window_days=window_days, as_of=_at(at, data))


def monthly() -> MonthlyStats:
    return monthly_stats(engine_data(), medication_changes=store.list_medication_changes())


def baseline(at: str | None = None, window_days: int = 90) -> BaselineStats:
    data = engine_data()
    return baseline_stats(data, as_of=_at(at, data), window_days=window_days)


def run_trigger_tests(only: list[str] | None = None, at: str | None = None) -> list[TriggerTest]:
    data = engine_data()
    defs = store.list_trigger_definitions()
    existing = {t.trigger_id: t for t in store.list_trigger_tests()}
    results = []
    for d in defs:
        if d.archived:
            continue
        if only and d.id not in only and d.name not in only:
            results.append(existing[d.id]) if d.id in existing else None
            continue
        hist = [h.model_dump() for h in existing[d.id].history] if d.id in existing else []
        results.append(test_trigger(data, d, as_of=_at(at, data), history=hist))
    results = adjust_bh([r for r in results if r is not None], {d.id: d for d in defs})
    store.save_trigger_tests(results)
    return results


def list_trigger_tests() -> list[TriggerTest]:
    tests = store.list_trigger_tests()
    if not tests and store.list_trigger_definitions():
        tests = run_trigger_tests()
    order = {"supported": 0, "emerging": 1, "watching": 2, "not_seen_so_far": 3, "unlikely": 4}
    return sorted(tests, key=lambda t: (order.get(str(t.rung.value if hasattr(t.rung, "value") else t.rung), 9), -(t.ratio or 0)))


def add_trigger(defn: TriggerDefinition) -> TriggerTest:
    d = store.upsert_trigger_definition(defn)
    tests = run_trigger_tests()
    return next(t for t in tests if t.trigger_id == d.id)


def clinic_report(window_days: int = 90, at: str | None = None, questions: list[str] | None = None) -> ClinicReport:
    data = engine_data()
    return build_clinic_report(
        data, as_of=_at(at, data), window_days=window_days, medication_changes=store.list_medication_changes(),
        triggers=list_trigger_tests(), questions=questions or store.get_kv("clinic_questions", []), sudep_last_discussed=store.get_kv("sudep_last_discussed"),
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
