import os, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[2] / "packages" / "contracts" / "py"))
os.environ.setdefault("DB_PATH", str(HERE.parent / "data" / "test.db"))
os.environ.setdefault("FORCE_MOCK", "1")
import pytest
from engine import import_family_workbook, EngineData, default_profile

@pytest.fixture(scope="session")
def diary():
    # The family's workbook and the names file are private and not in the repo; get them from the team.
    path = HERE.parent / "data" / "family_diary.xlsx"
    if not path.exists() or not (HERE.parent / "data" / "redact_names.json").exists():
        pytest.skip("private diary data (family_diary.xlsx, redact_names.json) not present")
    events, _ = import_family_workbook(path)
    return events

@pytest.fixture(scope="session")
def data(diary):
    return EngineData.from_models(diary, profile=default_profile())
