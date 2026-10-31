import json
from fastapi.testclient import TestClient


def test_mock_endpoints_serve_fixtures():
    from app.main import app
    c = TestClient(app)
    for path in ["/risk/now", "/stats/hourly", "/stats/monthly", "/stats/baseline", "/triggers", "/report/clinic", "/profile"]:
        r = c.get(path, params={"mock": 1}); assert r.status_code == 200, (path, r.text)


def test_live_endpoints_run_on_seeded_db(tmp_path):
    from app import store, service
    from app.main import app
    from scripts.seed import seed
    seed()
    c = TestClient(app)
    assert c.get("/health").json()["counts"]["events"] == 2598
    r = c.get("/risk/now", params={"at": "2026-08-21T18:30:00"}).json(); assert r["tier"] == "high"
    tap = c.post("/events/tap", json={}).json(); assert tap["source"] == "tap"
    tok = c.post("/live/token").json(); assert tok["mock"] is True and len(tok["tool_declarations"]) == 4
    res = c.post("/live/tool", json={"id": "1", "name": "log_seizure", "args": {"start_time": "2026-08-24T19:15:00+01:00", "duration_s": 90, "type": "impaired_awareness", "confidence": "probable", "context_tags": ["shower_bath"]}}).json()
    assert res["response"]["status"] == "saved"
    ex = c.post("/transcripts/extract", json={"transcript": "She had one about quarter past seven, maybe a minute and a half, her head went to the side, just out of the shower."}).json()
    assert ex["seizures"][0]["type"] == "impaired_awareness" and ex["seizures"][0]["duration_s"] == 90
    trig = c.post("/triggers", json={"name": "after the train", "kind": "exposure", "context_tag": "travel"}).json(); assert trig["rung"] in ("emerging", "watching", "supported")
    rep = c.get("/report/clinic").json(); assert rep["headline"]["total"] > 0
    ans = c.post("/analysis/ask", json={"question": "When in the day do seizures happen?"}).json(); assert ans["mock"] is True
