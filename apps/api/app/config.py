"""Runtime settings. Everything comes from environment variables (see .env.example); nothing is hard-coded twice."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]  # repo root
API_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    for candidate in (ROOT / ".env", API_ROOT / ".env"):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


class Settings(BaseModel):
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    live_model: str = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
    extract_model: str = os.getenv("GEMINI_EXTRACT_MODEL", "gemini-3.8-flash")
    analysis_model: str = os.getenv("GEMINI_ANALYSIS_MODEL", "gemini-4-argon")
    analysis_fallback_model: str = os.getenv("GEMINI_ANALYSIS_FALLBACK_MODEL", "gemini-3.8-flash")
    db_path: Path = Path(os.getenv("DB_PATH", str(API_ROOT / "data" / "app.db")))
    fixtures_dir: Path = Path(os.getenv("FIXTURES_DIR", str(ROOT / "packages" / "contracts" / "fixtures")))
    timezone: str = os.getenv("APP_TIMEZONE", "Europe/London")
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
    force_mock: bool = os.getenv("FORCE_MOCK", "0") == "1"

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key) and not self.force_mock


settings = Settings()
