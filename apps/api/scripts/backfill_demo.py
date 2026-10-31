"""Fill the gap between the end of the real diary and today with synthetic seizures drawn from her own patterns.

    python scripts/backfill_demo.py              # replace all synthetic rows with a fresh backfill up to now
    python scripts/backfill_demo.py --seed 7     # a different (still reproducible) draw
    python scripts/backfill_demo.py --remove     # delete every synthetic row, nothing else

The real diary ends 24 Aug 2026 but the app runs on the real clock, so "last 7 days" would be empty. This script
generates SeizureEvents from the day after the last real (non-synthetic, non-today) event up to now (Europe/London):
- seizures per day: negative binomial (Poisson if not over-dispersed) matching the mean and variance of her daily
  counts over the last 90 days of the real diary
- start hours: her last-365-day hour-of-day histogram (rows with a guessed clock time left out); minute uniform
- type, severity, awareness, duration and her own label: copied from a random real seizure of the last 365 days
- context tags and free-text factors: each drawn independently at its share across the whole real diary (factors
  come from keywords in her notes, e.g. "tired", "stress", "poor sleep")
Every row: synthetic=True, source="import", confidence="guess", notes="Synthetic demo data". Running it twice
replaces the previous synthetic rows, never duplicates them. Uses DB_PATH like the API.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2] / "packages" / "contracts" / "py"))

from contracts import SeizureEvent  # noqa: E402
from app import service, store  # noqa: E402
from app.config import settings  # noqa: E402

NOTE = "Synthetic demo data"
ID_PREFIX = "synthetic-"
FACTOR_KEYWORDS = {
    "Poor sleep": r"\b(bad|poor|little|no|short|late) (sleep|night)\b|didn'?t sleep|up late",
    "Tired": r"\btired|exhausted|fatigue",
    "Stress": r"\bstress|anxious|nervous|worried|\bexams?\b",
    "Missed dose": r"\b(missed|forgot|late)\b.{0,20}\b(dose|meds?|tablets?|pills?)\b|\bdose\b.{0,20}\b(missed|late|forgot)",
    "Skipped meal": r"\bhungry|skipped (a )?(meal|lunch|breakfast|dinner)|(not|hadn'?t) eaten|no (lunch|breakfast)",
    "Alcohol": r"\balcohol|\bwine\b|\bbeer\b",
}


def _val(x) -> str:
    return str(x.value if hasattr(x, "value") else x)


def remove_synthetic() -> int:
    ids = [e.id for e in store.list_events() if e.synthetic or (e.id or "").startswith(ID_PREFIX)]
    return store.delete_events(ids)


def generate(real: list[SeizureEvent], now: pd.Timestamp, seed: int = 42) -> list[SeizureEvent]:
    """Pure: synthetic events from the day after the last real event (not counting today) up to `now`."""
    tz = now.tz
    today = now.normalize()
    past = [e for e in real if pd.Timestamp(e.start_time).tz_convert(tz).normalize() < today]
    if not past:
        return []
    starts = pd.DatetimeIndex([pd.Timestamp(e.start_time).tz_convert(tz) for e in past])
    last_day = starts.max().normalize()
    first_new = (last_day.tz_localize(None) + pd.Timedelta(days=1))
    if first_new > today.tz_localize(None):
        return []
    rng = np.random.default_rng(seed)

    # seizures per day over her last 90 real days
    days = starts.tz_localize(None).normalize()
    idx = pd.date_range(last_day.tz_localize(None) - pd.Timedelta(days=89), last_day.tz_localize(None), freq="D")
    daily = pd.Series(days).value_counts().reindex(idx, fill_value=0)
    mean, var = float(daily.mean()), float(daily.var(ddof=1)) if len(daily) > 1 else float(daily.mean())

    def draw_count() -> int:
        if mean <= 0:
            return 0
        if var > mean * 1.05:
            n = mean * mean / (var - mean)
            return int(rng.negative_binomial(n, n / (n + mean)))
        return int(rng.poisson(mean))

    # last 365 days of real seizures: hour histogram and the pool to copy type/duration from
    year = [e for e, s in zip(past, starts) if s > last_day - pd.Timedelta(days=365)]
    timed = [e for e in year if _val(e.confidence) != "guess"] or year
    hours = np.array([pd.Timestamp(e.start_time).tz_convert(tz).hour for e in timed])
    hist = np.bincount(hours, minlength=24).astype(float)
    hour_p = hist / hist.sum()

    # tag and factor shares across the whole real diary
    n_all = len(past)
    tag_counts: dict[str, int] = {}
    for e in past:
        for t in e.context_tags or []:
            tag_counts[_val(t)] = tag_counts.get(_val(t), 0) + 1
    tag_p = {t: c / n_all for t, c in tag_counts.items()}
    factor_p = {f: sum(1 for e in past if e.notes and re.search(p, e.notes, re.I)) / n_all for f, p in FACTOR_KEYWORDS.items()}
    factor_p = {f: p for f, p in factor_p.items() if p > 0}

    out: list[SeizureEvent] = []
    for day in pd.date_range(first_new, today.tz_localize(None), freq="D"):
        k = draw_count()
        if k == 0:
            continue
        hs = rng.choice(24, size=k, p=hour_p)
        mins = rng.integers(0, 60, size=k)
        for i, (h, m) in enumerate(sorted(zip(hs.tolist(), mins.tolist()))):
            t = (day + pd.Timedelta(hours=int(h), minutes=int(m))).tz_localize(tz, ambiguous=True, nonexistent="shift_forward")
            if t >= now:
                continue
            src = year[int(rng.integers(len(year)))]
            tags = [t_ for t_, p in tag_p.items() if rng.random() < p]
            factors = [f for f, p in factor_p.items() if rng.random() < p]
            out.append(SeizureEvent.model_validate({
                "id": f"{ID_PREFIX}{day:%Y%m%d}-{int(h):02d}{int(m):02d}-{i}",
                "start_time": t.to_pydatetime(), "duration_s": src.duration_s, "duration_estimated": bool(src.duration_estimated),
                "type": _val(src.type), "severity": _val(src.severity), "awareness": _val(src.awareness) if src.awareness else "unknown",
                "original_label": src.original_label, "context_tags": tags, "factors": factors,
                "who_logged": "carer", "confidence": "guess", "source": "import", "notes": NOTE, "synthetic": True,
            }))
    return out


def backfill(seed: int = 42, now: pd.Timestamp | None = None) -> tuple[int, int]:
    """Replace every synthetic row with a fresh draw. Returns (removed, added)."""
    removed = remove_synthetic()
    now = now if now is not None else pd.Timestamp.now(tz=settings.timezone)
    real = [e for e in store.list_events() if not e.synthetic]
    new = generate(real, now, seed=seed)
    if new:
        store.add_events(new)
    return removed, len(new)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--remove", action="store_true", help="delete every synthetic row and stop")
    args = ap.parse_args(argv)
    if args.remove:
        n = remove_synthetic(); msg = f"removed {n} synthetic events"
    else:
        removed, added = backfill(seed=args.seed)
        msg = f"removed {removed}, added {added} synthetic events (seed {args.seed})"
    service.invalidate()
    if store.list_trigger_definitions():
        service.run_trigger_tests()  # the lab's numbers follow the data
    print(f"{msg}; db {settings.db_path}")


if __name__ == "__main__":
    main()
