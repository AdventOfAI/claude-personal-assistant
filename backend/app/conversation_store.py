import json
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas import ChatMessage

_MAX_MESSAGES = 400


def _safe_client_id(client_id: str) -> str:
    s = "".join(c for c in client_id if c.isalnum() or c in "-_")[:128]
    return s or "default"


_messages_adapter = TypeAdapter(list[ChatMessage])


class ConversationStore:
    def __init__(self, base: Path) -> None:
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, client_id: str) -> Path:
        return self._base / f"{_safe_client_id(client_id)}.json"

    def get(self, client_id: str) -> list[ChatMessage]:
        path = self._path(client_id)
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        return _messages_adapter.validate_json(raw)

    def save(self, client_id: str, messages: list[ChatMessage]) -> None:
        if len(messages) > _MAX_MESSAGES:
            messages = messages[-_MAX_MESSAGES:]
        path = self._path(client_id)
        path.write_text(
            json.dumps(
                [m.model_dump() for m in messages],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def clear(self, client_id: str) -> None:
        path = self._path(client_id)
        if path.exists():
            path.unlink()
