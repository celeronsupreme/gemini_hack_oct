import _paths  # noqa: F401
"""Deterministic analysis engine. Pure functions over EngineData; no I/O, no network."""
from .data import EngineData, default_profile, ensure_tz, half_life_for  # noqa: F401
from .risk import compute_risk, score_grid, thresholds  # noqa: F401
from .stats import hourly_stats, monthly_stats, baseline_stats, medication_change_effect, medication_changes_with_effects  # noqa: F401
from .triggers import test_trigger, adjust_bh  # noqa: F401
from .report import build_clinic_report  # noqa: F401
from .backtest import backtest  # noqa: F401
from .importer import import_family_workbook, import_generic_csv, preview_from_events, redact  # noqa: F401
