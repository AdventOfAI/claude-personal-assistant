# When imported as `backend.app.main`, `from app.*` needs `backend/` on sys.path.
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import asyncio
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter

from app.config import settings
from app.conversation_store import ConversationStore
from app.file_context import extract_text
from app.llm import complete_chat
from app.profile_store import ProfileStore
from app.schemas import (
    ChatMessage,
    ChatResponse,
    ConversationResponse,
    ProfilePutRequest,
    UserProfile,
)

app = FastAPI(title="Personalised Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = ProfileStore(settings.data_dir / "profiles")
conversations = ConversationStore(settings.data_dir / "conversations")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PUBLIC_DIR = PROJECT_ROOT / "public"

# On Vercel, requests often hit the Python app first; if we do not mount static files, `/` has no route → 404.
_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

_messages_adapter = TypeAdapter(list[ChatMessage])

# Starlette default per-part limit is 1MB for non-file fields; allow larger JSON transcripts.
_FORM_MAX_PART = 16 * 1024 * 1024


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profile", response_model=UserProfile)
def get_profile(client_id: str = "default") -> UserProfile:
    return store.get(client_id)


@app.put("/api/profile", response_model=UserProfile)
def put_profile(body: ProfilePutRequest, client_id: str = "default") -> UserProfile:
    store.save(client_id, body.profile)
    return body.profile


@app.get("/api/conversation", response_model=ConversationResponse)
def get_conversation(client_id: str = "default") -> ConversationResponse:
    return ConversationResponse(messages=conversations.get(client_id))


@app.delete("/api/conversation")
def clear_conversation(client_id: str = "default") -> dict[str, str]:
    conversations.clear(client_id)
    return {"status": "cleared"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request) -> ChatResponse:
    try:
        form = await request.form(max_part_size=_FORM_MAX_PART)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read upload: {e}") from e

    messages_raw = form.get("messages")
    if messages_raw is None or not isinstance(messages_raw, str):
        raise HTTPException(status_code=400, detail="Field 'messages' (JSON string) is required")

    raw_client = form.get("client_id")
    client_id = "default"
    if isinstance(raw_client, str) and raw_client.strip():
        client_id = raw_client.strip()

    try:
        parsed = _messages_adapter.validate_json(messages_raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid messages JSON: {e}") from e

    if not parsed:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    if parsed[-1].role != "user":
        raise HTTPException(status_code=400, detail="last message must be from the user")

    profile = store.get(client_id)

    upload = form.get("file")
    file_bytes: bytes | None = None
    file_name: str | None = None
    if upload is not None and hasattr(upload, "filename") and getattr(upload, "filename", None):
        fn = upload.filename
        if fn:
            file_name = fn
            file_bytes = await upload.read()

    file_text: str | None = None
    file_fname: str | None = None
    if file_bytes is not None and file_name:
        try:
            file_text = await asyncio.to_thread(extract_text, file_name, file_bytes)
            file_fname = file_name
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        text = await asyncio.to_thread(complete_chat, profile, parsed, file_text, file_fname)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception:
        raise HTTPException(status_code=502, detail="Claude request failed") from e

    assistant_msg = ChatMessage(role="assistant", content=text)
    conversations.save(client_id, [*parsed, assistant_msg])
    return ChatResponse(message=assistant_msg)


if _VERCEL and PUBLIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
elif not _VERCEL and FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.get("/api/debug")
async def debug():
    import os
    key = os.environ.get("ANTHROPIC_API_KEY")
    return {
        "key_present": key is not None,
        "key_prefix": key[:8] if key else None,
        "vercel": os.environ.get("VERCEL"),
        "model": settings.claude_model
    }