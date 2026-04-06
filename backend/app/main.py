# When imported as `backend.app.main`, `from app.*` needs `backend/` on sys.path.
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import asyncio
import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter

from app.config import settings
from app.conversation_store import ConversationStore
from app.file_context import extract_text
from app.llm import stream_chat
from app.profile_store import ProfileStore
from app.schemas import ChatMessage, ConversationResponse, ProfilePutRequest, UserProfile

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

# On Vercel, static UI is served from public/ via the CDN; do not mount StaticFiles here.
_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

_messages_adapter = TypeAdapter(list[ChatMessage])

# Starlette default per-part limit is 1MB for non-file fields; allow larger JSON transcripts.
_FORM_MAX_PART = 16 * 1024 * 1024


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


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


@app.post("/api/chat/stream")
async def chat_stream(request: Request) -> StreamingResponse:
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

    def event_stream():
        yield _sse({"type": "start"})
        full_reply = ""
        try:
            for chunk in stream_chat(profile, parsed, file_text, file_fname):
                if chunk:
                    full_reply += chunk
                    yield _sse({"type": "token", "text": chunk})
            yield _sse({"type": "done"})
            assistant_msg = ChatMessage(role="assistant", content=full_reply.strip())
            conversations.save(client_id, [*parsed, assistant_msg])
        except ValueError as e:
            yield _sse({"type": "error", "message": str(e)})
        except Exception:
            yield _sse({"type": "error", "message": "Claude request failed"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if not _VERCEL and FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
