"""Seed the database from the family diary and write every fixture from real engine output.

    python scripts/seed.py            # import diary + medication timeline + profile + demo triggers, then fixtures
    python scripts/seed.py --fixtures # fixtures only, from whatever is in the database

Names in notes are replaced with role words on import; the NHS number never leaves the workbook header.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2] / "packages" / "contracts" / "py"))

from contracts import Profile, TriggerDefinition  # noqa: E402
from engine import import_family_workbook, medication_changes_with_effects  # noqa: E402
from gemini import extract as gemini_extract, live as gemini_live  # noqa: E402
from app import service, store  # noqa: E402
from app.config import settings  # noqa: E402

DATA = HERE.parent / "data"

DEMO_PROFILE = Profile(
    display_name="", role="carer",
    seizure_type_labels={"Quiet and aware": "aware", "Head strongly to side, lots of saliva, cannot speak": "impaired_awareness", "Slack jaw, lose control of lips - dribbling": "impaired_awareness", "Tonic-Clonic": "convulsive", "Absence": "staring"},
    medications=[
        {"drug": "brivaracetam", "dose_mg": 100, "times": ["09:00"], "half_life_hours": 9},
        {"drug": "brivaracetam", "dose_mg": 150, "times": ["21:00"], "half_life_hours": 9},
        {"drug": "cenobamate", "dose_mg": 350, "times": ["19:00"], "half_life_hours": 50},
        {"drug": "clobazam", "dose_mg": 10, "times": [], "as_needed": True, "half_life_hours": 20},
    ],
    rescue_plan={"rescue_drug": "clobazam", "rescue_dose_mg": 10, "emergency_minutes_convulsive": 5, "emergency_minutes_other": 10, "call": ["999"], "notes": "Clobazam 10 mg to break a cluster; VNS magnet swipe if available."},
    sleeps_alone=False, photosensitive=False, menstruating=True, sleep_window={"start": "00:00", "end": "07:00"},
    custom_vocabulary=["brivaracetam", "cenobamate", "clobazam", "VNS", "quiet and aware", "head to the side"],
    consent={"gemini_processing": True, "accepted_at": "2026-10-31T12:00:00+00:00"},
)

DEMO_TRIGGERS = [
    TriggerDefinition(id="shower", name="hot shower or bath", kind="exposure", context_tag="shower_bath"),
    TriggerDefinition(id="period", name="period", kind="exposure", context_tag="period", literature_prior=True),
    TriggerDefinition(id="travel", name="travel", kind="exposure", context_tag="travel"),
    TriggerDefinition(id="exercise", name="exercise", kind="exposure", context_tag="exercise", window_hours=2),
    TriggerDefinition(id="upset", name="being upset", kind="exposure", context_tag="upset", literature_prior=True),
    TriggerDefinition(id="screens", name="screens", kind="exposure", context_tag="screen"),
    TriggerDefinition(id="swimming", name="swimming", kind="daily_factor"),
    TriggerDefinition(id="stress", name="stress", kind="daily_factor", checkin_field="stress", literature_prior=True),
]


def seed() -> None:
    store.reset_all()
    events, warnings = import_family_workbook(DATA / "family_diary.xlsx")
    store.add_events(events)
    store.save_profile(DEMO_PROFILE)
    for d in DEMO_TRIGGERS:
        store.upsert_trigger_definition(d)
    service.invalidate()
    tl = pd.read_csv(DATA / "medication_timeline.csv")
    tl = tl[tl["action"] != "state"]
    changes = medication_changes_with_effects(service.engine_data(), tl)
    store.save_medication_changes(changes)
    service.run_trigger_tests()
    print(f"seeded {len(events)} events, {len(changes)} medication changes, {len(DEMO_TRIGGERS)} triggers; warnings: {warnings}")


def fixtures() -> None:
    out = settings.fixtures_dir
    out.mkdir(parents=True, exist_ok=True)
    data = service.engine_data()
    last = data.events["start_time"].max()
    demo_at = (last.normalize() + pd.Timedelta(hours=18, minutes=30)).isoformat()  # an evening on the last logged day
    dump = lambda name, model: (out / f"{name}.json").write_text(json.dumps(model if isinstance(model, (list, dict)) else model.model_dump(mode="json"), indent=1, default=str))
    dump("profile", store.get_profile())
    dump("events", [e.model_dump(mode="json") for e in store.list_events()[-200:]])
    dump("doses", [])
    dump("checkins", [])
    dump("risk_now", service.risk_now(demo_at))
    dump("stats_hourly", service.hourly(demo_at))
    dump("stats_monthly", service.monthly())
    dump("stats_baseline", service.baseline(demo_at))
    dump("triggers", [t.model_dump(mode="json") for t in service.list_trigger_tests()])
    dump("report_clinic", service.clinic_report(at=demo_at))
    dump("live_token", gemini_live.create_live_token(store.get_profile(), ["hot shower or bath"]).model_copy(update={"mock": True, "token": "mock-token"}))
    dump("extract", gemini_extract._mock_extract("She had one about quarter past seven, maybe a minute and a half, her head went to the side, she'd just got out of the shower.", pd.Timestamp(demo_at).to_pydatetime()))
    dump("analysis", {"question": "Has moving the afternoon dose helped?", "answer": "Mock fixture: see /analysis/ask with Gemini configured.", "numbers": {}, "chart_png_base64": None, "caveats": ["fixture"], "model": "mock", "mock": True})
    dump("import_preview", {"job_id": "fixture", "source_name": "family_diary.xlsx", "sheets": ["Seizure Data"], "column_mapping": {"Seizure Date": "start_time (date)", "Time": "start_time (clock)", "Duration seconds (Calc)": "duration_s", "Type": "type + original_label", "Seizure Severity (H/L)": "severity", "Notes": "notes + context_tags"}, "assumptions": ["Times are Europe/London local time", "Day/month order read as typed (d/m/y)"], "warnings": ["47 rows had no clock time; set to 12:00 and marked as guesses"], "preview_rows": [e.model_dump(mode="json") for e in store.list_events()[:10]], "total_rows": store.counts()["events"], "label_mapping": DEMO_PROFILE.seizure_type_labels})
    print(f"fixtures written to {out} (demo time {demo_at})")


if __name__ == "__main__":
    if "--fixtures" not in sys.argv:
        seed()
    fixtures()
