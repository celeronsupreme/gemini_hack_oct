"""Make `contracts` importable from anywhere in apps/api without PYTHONPATH gymnastics."""
import sys
from pathlib import Path

_CONTRACTS = Path(__file__).resolve().parents[2] / "packages" / "contracts" / "py"
if str(_CONTRACTS) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS))
_API = Path(__file__).resolve().parent
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))
