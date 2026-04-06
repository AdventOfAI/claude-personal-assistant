import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")


def _default_data_dir() -> Path:
    """Local dev uses backend/data. Vercel has a read-only FS except /tmp."""
    override = os.environ.get("DATA_DIR", "").strip()
    if override:
        return Path(override)
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        return Path("/tmp/pa-data")
    return _BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    data_dir: Path = Field(default_factory=_default_data_dir)


settings = Settings()
