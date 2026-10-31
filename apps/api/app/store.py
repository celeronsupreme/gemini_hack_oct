"""SQLite storage. Each row keeps its full contract model as JSON (`payload`) plus a few indexed columns, so the
contract stays the single source of truth and the schema never drifts from the database."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Iterable, TypeVar

import pandas as pd
from sqlalchemy import text
from sqlmodel import Field, Session, SQLModel, create_engine, select

from contracts import CheckIn, Dose, MedicationChange, Profile, SeizureEvent, TriggerDefinition, TriggerTest
from engine import EngineData, default_profile
from .config import settings

T = TypeVar("T")


class EventRow(SQLModel, table=True):
    __tablename__ = "seizure_event"
    id: str = Field(primary_key=True)
    start_time_utc: str = Field(index=True)
    type: str = Field(index=True)
    severity: str
    payload: str
    updated_at: str


class DoseRow(SQLModel, table=True):
    __tablename__ = "dose"
    id: str = Field(primary_key=True)
    scheduled_time_utc: str = Field(index=True)
    drug: str
    payload: str
    updated_at: str


class CheckInRow(SQLModel, table=True):
    __tablename__ = "checkin"
    id: str = Field(primary_key=True)
    date: str = Field(index=True)
    payload: str
    updated_at: str


class SymptomRow(SQLModel, table=True):
    __tablename__ = "symptom"
    id: str = Field(primary_key=True)
    time_utc: str = Field(index=True)
    text: str


class ExposureRow(SQLModel, table=True):
    __tablename__ = "exposure"
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    start_utc: str = Field(index=True)
    end_utc: str
    source: str


class TriggerDefRow(SQLModel, table=True):
    __tablename__ = "trigger_definition"
    id: str = Field(primary_key=True)
    name: str
    payload: str


class TriggerTestRow(SQLModel, table=True):
    __tablename__ = "trigger_test"
    trigger_id: str = Field(primary_key=True)
    payload: str
    computed_at: str


class MedicationChangeRow(SQLModel, table=True):
    __tablename__ = "medication_change"
    id: str = Field(primary_key=True)
    date: str = Field(index=True)
    payload: str


class KVRow(SQLModel, table=True):
    __tablename__ = "kv"
    key: str = Field(primary_key=True)
    value: str


_engine = None


def engine():
    global _engine
    if _engine is None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{settings.db_path}", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
        with _engine.connect() as c:
            c.execute(text("PRAGMA journal_mode=WAL"))
    return _engine


def session() -> Session:
    return Session(engine())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


# ---------- writes ----------
def add_events(events: Iterable[SeizureEvent]) -> list[SeizureEvent]:
    out = []
    with session() as s:
        for e in events:
            if not e.id:
                e = e.model_copy(update={"id": str(uuid.uuid4())})
            s.merge(EventRow(id=e.id, start_time_utc=_utc(e.start_time), type=str(e.type.value if hasattr(e.type, "value") else e.type), severity=str(e.severity.value if hasattr(e.severity, "value") else e.severity), payload=e.model_dump_json(), updated_at=_now()))
            out.append(e)
        s.commit()
    bump_version()
    return out


def add_doses(doses: Iterable[Dose]) -> list[Dose]:
    out = []
    with session() as s:
        for d in doses:
            if not d.id:
                d = d.model_copy(update={"id": str(uuid.uuid4())})
            s.merge(DoseRow(id=d.id, scheduled_time_utc=_utc(d.scheduled_time), drug=d.drug, payload=d.model_dump_json(), updated_at=_now()))
            out.append(d)
        s.commit()
    bump_version()
    return out


def add_checkins(checkins: Iterable[CheckIn]) -> list[CheckIn]:
    out = []
    with session() as s:
        for c in checkins:
            cid = c.id or f"checkin-{c.date}"
            c = c.model_copy(update={"id": cid})
            s.merge(CheckInRow(id=cid, date=str(c.date), payload=c.model_dump_json(), updated_at=_now()))
            out.append(c)
        s.commit()
    bump_version()
    return out


def add_symptom(time, text_: str) -> str:
    sid = str(uuid.uuid4())
    with session() as s:
        s.add(SymptomRow(id=sid, time_utc=_utc(time), text=text_)); s.commit()
    bump_version()
    return sid


def add_exposures(rows: Iterable[tuple[str, datetime, datetime, str]]) -> int:
    n = 0
    with session() as s:
        for name, start, end, src in rows:
            s.add(ExposureRow(id=str(uuid.uuid4()), name=name, start_utc=_utc(start), end_utc=_utc(end), source=src)); n += 1
        s.commit()
    bump_version()
    return n


def upsert_trigger_definition(d: TriggerDefinition) -> TriggerDefinition:
    if not d.id:
        d = d.model_copy(update={"id": str(uuid.uuid4())})
    if not d.created_at:
        d = d.model_copy(update={"created_at": datetime.now(timezone.utc)})
    with session() as s:
        s.merge(TriggerDefRow(id=d.id, name=d.name, payload=d.model_dump_json())); s.commit()
    return d


def save_trigger_tests(tests: Iterable[TriggerTest]) -> None:
    with session() as s:
        for t in tests:
            s.merge(TriggerTestRow(trigger_id=t.trigger_id, payload=t.model_dump_json(), computed_at=_now()))
        s.commit()


def save_medication_changes(changes: Iterable[MedicationChange]) -> None:
    with session() as s:
        for c in changes:
            s.merge(MedicationChangeRow(id=f"{c.date}-{c.drug}-{c.action}", date=str(c.date), payload=c.model_dump_json()))
        s.commit()


def save_profile(p: Profile) -> None:
    with session() as s:
        s.merge(KVRow(key="profile", value=p.model_dump_json())); s.commit()
    bump_version()


def set_kv(key: str, value) -> None:
    with session() as s:
        s.merge(KVRow(key=key, value=json.dumps(value, default=str))); s.commit()


def get_kv(key: str, default=None):
    with session() as s:
        row = s.get(KVRow, key)
        return json.loads(row.value) if row else default


def bump_version() -> None:
    set_kv("data_version", _now())


def data_version() -> str:
    return get_kv("data_version", "0")


# ---------- reads ----------
def _rows(model, stmt=None):
    with session() as s:
        return list(s.exec(stmt if stmt is not None else select(model)).all())


def list_events(start=None, end=None) -> list[SeizureEvent]:
    stmt = select(EventRow)
    if start is not None:
        stmt = stmt.where(EventRow.start_time_utc >= _utc(start))
    if end is not None:
        stmt = stmt.where(EventRow.start_time_utc < _utc(end))
    return [SeizureEvent.model_validate_json(r.payload) for r in _rows(EventRow, stmt.order_by(EventRow.start_time_utc))]


def list_doses(start=None, end=None) -> list[Dose]:
    stmt = select(DoseRow)
    if start is not None:
        stmt = stmt.where(DoseRow.scheduled_time_utc >= _utc(start))
    if end is not None:
        stmt = stmt.where(DoseRow.scheduled_time_utc < _utc(end))
    return [Dose.model_validate_json(r.payload) for r in _rows(DoseRow, stmt.order_by(DoseRow.scheduled_time_utc))]


def list_checkins() -> list[CheckIn]:
    return [CheckIn.model_validate_json(r.payload) for r in _rows(CheckInRow, select(CheckInRow).order_by(CheckInRow.date))]


def list_symptoms() -> list[tuple[datetime, str]]:
    return [(pd.Timestamp(r.time_utc).to_pydatetime(), r.text) for r in _rows(SymptomRow)]


def list_exposures() -> list[tuple[str, datetime, datetime, str]]:
    return [(r.name, pd.Timestamp(r.start_utc).to_pydatetime(), pd.Timestamp(r.end_utc).to_pydatetime(), r.source) for r in _rows(ExposureRow)]


def list_trigger_definitions() -> list[TriggerDefinition]:
    return [TriggerDefinition.model_validate_json(r.payload) for r in _rows(TriggerDefRow)]


def list_trigger_tests() -> list[TriggerTest]:
    return [TriggerTest.model_validate_json(r.payload) for r in _rows(TriggerTestRow)]


def list_medication_changes() -> list[MedicationChange]:
    return [MedicationChange.model_validate_json(r.payload) for r in _rows(MedicationChangeRow, select(MedicationChangeRow).order_by(MedicationChangeRow.date))]


def get_profile() -> Profile:
    with session() as s:
        row = s.get(KVRow, "profile")
        return Profile.model_validate_json(row.value) if row else default_profile()


def counts() -> dict:
    with session() as s:
        return {
            "events": s.exec(select(EventRow)).all().__len__(), "doses": s.exec(select(DoseRow)).all().__len__(),
            "checkins": s.exec(select(CheckInRow)).all().__len__(), "exposures": s.exec(select(ExposureRow)).all().__len__(),
            "triggers": s.exec(select(TriggerDefRow)).all().__len__(),
        }


def load_engine_data() -> EngineData:
    return EngineData.from_models(
        events=list_events(), doses=list_doses(), checkins=list_checkins(), profile=get_profile(),
        symptoms=list_symptoms(), exposures=list_exposures(), tz=settings.timezone,
    )


def reset_all() -> None:
    with session() as s:
        for model in (EventRow, DoseRow, CheckInRow, SymptomRow, ExposureRow, TriggerDefRow, TriggerTestRow, MedicationChangeRow, KVRow):
            s.exec(text(f"DELETE FROM {model.__tablename__}"))  # type: ignore[attr-defined]
        s.commit()
    bump_version()
