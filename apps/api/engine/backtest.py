"""Backtest the risk score the way the brief did: fit nothing, just score every hour of a held-out period with the
engine (thresholds from the trailing 90 days as of each day) and measure AUC against "a seizure in the next N hours"."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .data import EngineData, to_ns
from .risk import score_grid, HIGH_SHARE, MEDIUM_SHARE


def backtest(data: EngineData, test_start: str, test_end: str, horizon_hours: int = 3, step_days: int = 7) -> dict:
    """Walk forward in `step_days` blocks: thresholds and histogram come from data before each block."""
    tz = data.tz
    t0 = pd.Timestamp(test_start, tz=tz); t1 = pd.Timestamp(test_end, tz=tz)
    ev_utc = to_ns(data.events["start_time"])
    rows = []
    block_start = t0
    while block_start < t1:
        block_end = min(block_start + pd.Timedelta(days=step_days), t1)
        as_of = block_start
        grid = pd.date_range(block_start, block_end - pd.Timedelta(hours=1), freq="h", tz=tz)
        if len(grid) == 0:
            break
        g = score_grid(data, grid, as_of=as_of)
        # thresholds from the trailing 90 days as of block start
        cal = score_grid(data, pd.date_range(as_of - pd.Timedelta(days=90), as_of, freq="h", tz=tz), as_of=as_of)
        awake = cal[~cal["overnight"]]["score"]
        high = float(awake.quantile(1 - HIGH_SHARE)); medium = float(awake.quantile(1 - MEDIUM_SHARE))
        t_utc = to_ns(grid)
        a = np.searchsorted(ev_utc, t_utc, side="left"); b = np.searchsorted(ev_utc, t_utc + int(pd.Timedelta(hours=horizon_hours).value), side="left")
        g["y"] = (b - a) > 0
        g["tier"] = np.where(g["score"] >= high, "high", np.where(g["score"] >= medium, "medium", "low"))
        rows.append(g)
        block_start = block_end
    g = pd.concat(rows)
    awake = g[~g["overnight"]]
    out = {
        "hours": int(len(awake)), "base_rate": round(float(awake["y"].mean()), 4),
        "auc": round(float(roc_auc_score(awake["y"], awake["score"])), 3) if awake["y"].nunique() > 1 else None,
        "tiers": {},
    }
    for tier, sub in awake.groupby("tier"):
        out["tiers"][tier] = {"hours_pct": round(len(sub) / len(awake) * 100, 1), "hit_rate": round(float(sub["y"].mean()), 4)}
    hi = out["tiers"].get("high", {}).get("hit_rate"); lo = out["tiers"].get("low", {}).get("hit_rate")
    out["high_over_low"] = round(hi / lo, 2) if hi and lo else None
    return out
