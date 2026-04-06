import json
from pathlib import Path

from app.schemas import UserProfile


def _safe_client_id(client_id: str) -> str:
    s = "".join(c for c in client_id if c.isalnum() or c in "-_")[:128]
    return s or "default"


class ProfileStore:
    def __init__(self, base: Path) -> None:
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, client_id: str) -> Path:
        return self._base / f"{_safe_client_id(client_id)}.json"

    def get(self, client_id: str) -> UserProfile:
        path = self._path(client_id)
        if not path.exists():
            return UserProfile()
        return UserProfile.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, client_id: str, profile: UserProfile) -> None:
        path = self._path(client_id)
        path.write_text(
            json.dumps(profile.model_dump(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
