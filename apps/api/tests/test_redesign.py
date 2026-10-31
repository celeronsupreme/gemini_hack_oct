"""UI-redesign backend: DELETE /events, factor-matching triggers, short reason text, report window, demo backfill."""
from datetime import timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from contracts import Profile, SeizureEvent, TriggerDefinition
from engine import EngineData, compute_risk, default_profile
from engine import test_trigger as run_trigger_test
from engine.risk import COMPONENTS, _reason_text


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def _event(start, **kw):
    return SeizureEvent.model_validate({"start_time": start, "type": "aware", "severity": "mild", "who_logged": "carer", "confidence": "probable", "source": "manual", **kw})


def test_delete_event_and_patch_new_fields(client):
    e = client.post("/events", json={"start_time": "2026-10-31T10:00:00+00:00", "type": "unsure", "severity": "mild", "who_logged": "carer", "confidence": "probable", "source": "tap"}).json()
    assert e["factors"] == [] and e["recovery_text"] is None and e["synthetic"] is False
    p = client.patch(f"/events/{e['id']}", json={"factors": ["Skipped meal", "Poor sleep"], "recovery_text": "Sleepy for an hour"}).json()
    assert p["factors"] == ["Skipped meal", "Poor sleep"] and p["recovery_text"] == "Sleepy for an hour"
    got = next(x for x in client.get("/events", params={"from": "2026-10-31"}).json() if x["id"] == e["id"])
    assert got["factors"] == ["Skipped meal", "Poor sleep"]
    v = client.get("/health").json()["data_version"]
    assert client.delete(f"/events/{e['id']}").json() == {"ok": True}
    assert client.get("/health").json()["data_version"] != v
    assert all(x["id"] != e["id"] for x in client.get("/events", params={"from": "2026-10-31"}).json())
    assert client.delete(f"/events/{e['id']}").status_code == 404


def test_trigger_matches_free_text_factors(diary):
    base = pd.Timestamp("2026-08-25 12:00", tz="Europe/London")
    few = [_event((base + timedelta(days=i)).isoformat(), factors=["skipped MEAL"]) for i in range(3)]
    t = run_trigger_test(EngineData.from_models(list(diary) + few, profile=default_profile()), TriggerDefinition(id="m", name="Skipped meal", kind="exposure"))
    assert t.rung == "watching" and t.exposure_units == 3 and t.units_to_next_verdict == 7
    many = [_event((base + timedelta(days=i)).isoformat(), factors=["Skipped meal at lunch" if i % 2 else "Skipped meal"], type="convulsive", severity="severe") for i in range(12)]
    t = run_trigger_test(EngineData.from_models(list(diary) + many, profile=default_profile()), TriggerDefinition(id="m", name="skipped meal", kind="exposure"))
    assert t.exposure_units == 12 and t.method.startswith("notes only")
    assert t.rung == "emerging", "factor-only evidence has no denominator and is capped at emerging"
    none = run_trigger_test(EngineData.from_models(diary, profile=default_profile()), TriggerDefinition(id="m", name="Skipped meal", kind="exposure"))
    assert none.rung == "watching" and none.exposure_units == 0


def test_post_trigger_without_tag_is_watching(client):
    t = client.post("/triggers", json={"name": "Skipped meal", "kind": "exposure"})
    assert t.status_code == 200, t.text
    assert t.json()["rung"] == "watching"


def test_reason_text_is_short_and_third_person(data):
    hist = data.events["start_time"].dt.hour.value_counts().reindex(range(24), fill_value=0).to_numpy(dtype=float)
    carer = data
    self_data = EngineData.from_models([], profile=Profile.model_validate({**default_profile().model_dump(), "role": "self"}))
    for d, word in ((carer, "her"), (self_data, "your")):
        texts = set()
        for c in COMPONENTS:
            for h in range(24):
                for pts in (0.3, 0.5, 1.0, 1.5, 2.5, 4.0):
                    for n in (1, 2, 3, 12, 40):
                        row = pd.Series({"hour": h, "today_count_n": n, "hours_since_last_n": n / 8, "last7_n": n})
                        texts.add(_reason_text(c, pts, row, d, hist, int(hist.sum())))
        assert max(len(t) for t in texts) <= 40, max(texts, key=len)
        assert any(word in t for t in texts)
        assert not any("%" in t or "seizure" in t.lower() for t in texts)
    assert "7 pm–10 pm is her busiest stretch" in {_reason_text("hour_band", 3.0, pd.Series({"hour": 19, "today_count_n": 0, "hours_since_last_n": 9, "last7_n": 0}), carer, hist, int(hist.sum()))}
    r = compute_risk(data, pd.Timestamp("2026-08-21 18:30", tz=data.tz))
    assert all(len(x.text) <= 40 and x.factor in COMPONENTS for x in r.reasons)


def test_report_window_accepts_up_to_400(client):
    r = client.get("/report/clinic", params={"window": 365})
    assert r.status_code == 200, r.text
    assert (pd.Timestamp(r.json()["window_end"]) - pd.Timestamp(r.json()["window_start"])).days == 365
    assert client.get("/report/clinic", params={"window": 400}).status_code == 200
    assert client.get("/report/clinic", params={"window": 401}).status_code == 422
    assert client.get("/report/clinic", params={"window": 0}).status_code == 422


def test_backfill_on_temp_db(tmp_path, monkeypatch, diary):
    from app import store
    from app.config import settings
    from scripts import backfill_demo
    monkeypatch.setattr(settings, "db_path", tmp_path / "backfill.db")
    monkeypatch.setattr(store, "_engine", None)
    store.add_events(diary)
    now = pd.Timestamp("2026-10-31 15:30", tz="Europe/London")
    today_real = _event("2026-10-31T09:00:00+00:00", source="tap")
    store.add_events([today_real])
    removed, added = backfill_demo.backfill(seed=1, now=now)
    assert removed == 0 and added > 30  # ~68 days at her recent rate
    syn = [e for e in store.list_events() if e.synthetic]
    assert len(syn) == added
    assert all(e.source == "import" and e.confidence == "guess" and e.notes == "Synthetic demo data" for e in syn)
    assert min(e.start_time for e in syn) >= pd.Timestamp("2026-08-25", tz="Europe/London")
    assert max(e.start_time for e in syn) < now
    removed2, added2 = backfill_demo.backfill(seed=1, now=now)
    assert (removed2, added2) == (added, added), "running twice replaces, never duplicates"
    assert sorted(e.id for e in store.list_events() if e.synthetic) == sorted(e.id for e in syn)
    assert backfill_demo.remove_synthetic() == added
    assert store.counts()["events"] == len(diary) + 1, "real rows, including today's tap, are untouched"
