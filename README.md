# Personalised Assistant

A small web chat app that uses **Claude** (Anthropic) on the backend, with light **personalisation**, optional **file context** (including PDFs), and **persisted profile + conversation** per browser.

## Features

- **Claude via FastAPI** — Messages API (non-streaming JSON response).
- **Profile** — Display name, reply tone (brief / balanced / friendly / formal), “about you”, and extra instructions; injected into the system prompt and stored under `backend/data/profiles/`.
- **Chat history** — Conversation saved server-side and reloaded on return (`backend/data/conversations/`). Clear with **Clear chat** in the UI.
- **Anonymous identity** — A `client_id` UUID in `localStorage` ties profile + history to this browser (no login).
- **Attachments** — Upload text-like files or PDFs; text is extracted (PDF via `pypdf`, AES needs `cryptography`) and added to context for that turn.
- **Markdown rendering** — Assistant messages are rendered as Markdown (headings, bold, lists, code blocks) with sanitization (`marked` + `DOMPurify`, loaded from esm.sh).

## Requirements

- Python **3.11+** (3.13 tested)
- An [Anthropic API key](https://console.anthropic.com/)

## Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and set `ANTHROPIC_API_KEY`. Optionally set `CLAUDE_MODEL` (default in `app/config.py` is `claude-sonnet-4-20250514`).

Run the server **from `backend`** so the `app` package resolves:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** — the API and static UI are served together.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `CLAUDE_MODEL` | No | Model id (defaults in `app/config.py`) |

`python-dotenv` loads `backend/.env` automatically (path is fixed relative to the config module, so it works whether you start uvicorn from `backend` or the repo root).

## Project layout

```
backend/
  app/
    main.py              # FastAPI routes, chat API, static mount
    config.py            # Settings + .env
    llm.py               # Claude Messages API + system prompt
    schemas.py           # Pydantic models
    profile_store.py     # JSON profiles per client_id
    conversation_store.py
    file_context.py      # PDF / text extraction for uploads
  requirements.txt
  .env.example
frontend/
  index.html
  app.js                 # Chat UI, multipart + JSON
  markdown.js            # Markdown + sanitize (CDN imports)
  styles.css
build.py                 # Vercel build: copies frontend/ → public/
pyproject.toml           # Dependencies + Vercel build script
public/                  # Generated on deploy (gitignored); CDN-served UI on Vercel
```

Data files (ignored by git) live under `backend/data/` locally, or `/tmp/pa-data` on Vercel (see below):

- `profiles/<client_id>.json`
- `conversations/<client_id>.json`

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Health check |
| `GET` / `PUT` | `/api/profile?client_id=…` | Read / update profile |
| `GET` / `DELETE` | `/api/conversation?client_id=…` | Load / clear saved messages |
| `POST` | `/api/chat` | Multipart: `messages` (JSON string), `client_id`, optional `file`; JSON `{ "message": { "role", "content" } }` |

Locally, static files are mounted from **`frontend/`** after API routes. On Vercel, **`build.py`** copies assets to **`public/`**, and the app **mounts `public/`** when `VERCEL` is set (otherwise `/` would hit FastAPI with no route and return **404**). The FastAPI app still handles **`/api/*`** first.

## Deploying on Vercel

This repo includes a **zero-config style** layout compatible with [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi) (CLI **48.1.8+**).

1. **Root entrypoint** — **`main.py`** adds `backend/` to `sys.path` and exposes the FastAPI `app`. **`pyproject.toml`** includes **`[project.scripts] app = "main:app"`** so Vercel can resolve the app explicitly.
2. **Project root** — In the Vercel dashboard, set **Root Directory** to the **repository root** (where `main.py` and `pyproject.toml` live), **not** `backend`. If you must use Root Directory `backend`, use **`backend/main.py`** as the file that defines `app` (that file imports `from app.main import app` only).
3. **Build** — `pyproject.toml` runs `python build.py`, which copies `frontend/*` → **`public/`**. On Vercel, the app **mounts `public/`** in FastAPI so `/` serves the UI (see main app section above).
4. **Environment variables** — In the Vercel project dashboard, set **`ANTHROPIC_API_KEY`** (and optionally **`CLAUDE_MODEL`**). Do **not** rely on committing `backend/.env`.
5. **Data persistence** — Serverless functions have **no durable disk**. Profile and conversation JSON files are written under **`/tmp/pa-data`** when Vercel env is detected, which is **ephemeral** (can disappear between cold starts). For real persistence, add an external store (e.g. Vercel KV, Postgres, or Blob) and point **`DATA_DIR`** at a mounted path if you add one later.

If you still see **“FastAPI `app` must be importable from a top-level module”**, confirm **Root Directory** is the repo root (or use **`backend/main.py`** with Root Directory `backend`), and that **`[project.scripts] app = "main:app"`** is in **`pyproject.toml`**.

```bash
# From the repo root (after installing the Vercel CLI)
vercel
```

Use **`vercel dev`** to emulate the platform locally if needed.

### Limitations on Vercel

- Long Claude replies may hit [function duration limits](https://vercel.com/docs/functions/limitations) depending on your plan.
- **`public/`** is listed in `.gitignore`; it is produced by **`build.py`** on each deploy.

## Security notes

- Never commit `backend/.env`. Use `.env.example` as a template only.
- Assistant output is passed through **DOMPurify** before `innerHTML`; user messages stay plain text.
- This is a **local / dev-oriented** setup: CORS is wide open, and there is no authentication.

## Licence

Use and modify as you like for your own projects.
