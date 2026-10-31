"""Handlers for the voice agent's tools. The browser forwards each Live tool call here (POST /live/tool); we validate
against the contract, write to the store, and return what the model should say back."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import pandas as pd

from contracts import Dose, SeizureEvent
from engine import ensure_tz
from engine.importer import redact
from app import store, service
from app.config import settings
from zoneinfo import ZoneInfo

SEVERE_TYPES = {"impaired_awareness", "convulsive", "drop"}


def _parse_time(value: str | None, tz: ZoneInfo) -> pd.Timestamp:
    if not value:
        return pd.Timestamp.now(tz=tz)
    try:
        return ensure_tz(value, tz)
    except Exception:
        return pd.Timestamp.now(tz=tz)


def log_seizure(args: dict[str, Any]) -> dict[str, Any]:
    tz = ZoneInfo(settings.timezone)
    start = _parse_time(args.get("start_time"), tz)
    typ = args.get("type", "unsure")
    rescue = None
    if args.get("rescue_drug"):
        rescue = {"drug": args["rescue_drug"], "dose_mg": args.get("rescue_dose_mg"), "time": None}
    ev = SeizureEvent(
        id=args.get("id") or str(uuid.uuid4()), start_time=start.to_pydatetime(),
        duration_s=int(args["duration_s"]) if args.get("duration_s") is not None else None,
        duration_estimated=bool(args.get("duration_estimated", False)), still_going=bool(args.get("still_going", False)),
        type=typ, severity="severe" if typ in SEVERE_TYPES else "mild",
        awareness=args.get("awareness") or ("kept" if typ == "aware" else ("impaired" if typ in ("impaired_awareness", "staring") else ("lost" if typ == "convulsive" else "unknown"))),
        asleep_at_onset=args.get("asleep_at_onset"), recovered_at=(pd.Timestamp.now(tz=tz).to_pydatetime() if args.get("recovered") else None),
        injury=args.get("injury"), rescue_med=rescue, warning_before=args.get("warning_before"), warning_text=args.get("warning_text"),
        context_tags=[t for t in (args.get("context_tags") or []) if isinstance(t, str)], notes=redact(args.get("notes")) or None,
        who_logged="carer" if store.get_profile().role == "carer" else "patient", confidence=args.get("confidence", "probable"), source="voice",
    )
    existing = next((e for e in store.list_events() if e.id == ev.id), None) if args.get("id") else None
    if existing is not None:
        # Updating the event the one-tap timer created: keep everything it knows, and its timed start/duration win.
        fresh = {k: v for k, v in ev.model_dump().items() if v not in (None, [], "")}
        if str(existing.source) == "tap":
            fresh.pop("start_time", None)
            if existing.duration_s:
                fresh.pop("duration_s", None); fresh.pop("duration_estimated", None)
        ev = SeizureEvent.model_validate({**existing.model_dump(), **fresh, "still_going": False})
    store.add_events([ev]); service.invalidate()
    risk = service.risk_now()
    return {"status": "saved", "event_id": ev.id, "say": f"Saved. Risk now is {risk.tier}.", "risk_tier": risk.tier}


def log_dose(args: dict[str, Any]) -> dict[str, Any]:
    tz = ZoneInfo(settings.timezone)
    sched = _parse_time(args.get("scheduled_time"), tz)
    taken = _parse_time(args["taken_time"], tz) if args.get("taken_time") and not args.get("skipped") else None
    drug = args.get("drug", "")
    dose_mg = args.get("dose_mg")
    if dose_mg is None:
        for m in store.get_profile().medications:
            if m.drug.lower() in drug.lower() or drug.lower() in m.drug.lower():
                dose_mg = m.dose_mg; break
    d = Dose(id=str(uuid.uuid4()), drug=drug, dose_mg=float(dose_mg or 0), scheduled_time=sched.to_pydatetime(), taken_time=taken.to_pydatetime() if taken is not None else None, skipped=bool(args.get("skipped", False)), reason=args.get("reason"), source="voice")
    store.add_doses([d]); service.invalidate()
    return {"status": "saved", "dose_id": d.id, "say": "Dose noted."}


def log_symptom(args: dict[str, Any]) -> dict[str, Any]:
    tz = ZoneInfo(settings.timezone)
    sid = store.add_symptom(_parse_time(args.get("time"), tz), redact(args.get("text", "")))
    service.invalidate()
    return {"status": "saved", "symptom_id": sid, "say": "Noted; I will keep an eye on the next few hours."}


def get_todays_meds(args: dict[str, Any]) -> dict[str, Any]:
    tz = ZoneInfo(settings.timezone)
    now = pd.Timestamp.now(tz=tz)
    today = now.normalize()
    doses = store.list_doses(today, today + pd.Timedelta(days=1))
    out = []
    for m in store.get_profile().medications:
        for hhmm in (m.times or []):
            hh, mm = (int(x) for x in hhmm.split(":"))
            sched = today + pd.Timedelta(hours=hh, minutes=mm)
            logged = [d for d in doses if d.drug.lower().startswith(m.drug.lower().split()[0]) and abs((pd.Timestamp(d.scheduled_time) - sched).total_seconds()) < 3600]
            out.append({"drug": m.drug, "dose_mg": m.dose_mg, "scheduled": hhmm, "due": sched <= now, "taken": bool(logged and logged[0].taken_time), "skipped": bool(logged and logged[0].skipped)})
    return {"doses": out}


HANDLERS = {"log_seizure": log_seizure, "log_dose": log_dose, "log_symptom": log_symptom, "get_todays_meds": get_todays_meds}


def handle(name: str, args: dict[str, Any]) -> dict[str, Any]:
    fn = HANDLERS.get(name)
    if fn is None:
        return {"status": "error", "say": f"Unknown tool {name}"}
    try:
        return fn(args or {})
    except Exception as e:  # the model must get something back or the session stalls
        return {"status": "error", "say": "I couldn't save that; could you repeat the time?", "error": str(e)}
