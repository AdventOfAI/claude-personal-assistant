"""
Vercel entrypoint: FastAPI `app` must be importable from a top-level module.
See https://vercel.com/docs/frameworks/backend/fastapi

Prefer this file over index.py — Vercel’s detector often looks for main.py first.
"""
from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent / "backend"
if not _backend.is_dir():
    raise RuntimeError(
        f"Expected a 'backend' directory next to main.py at {_backend}. "
        "Deploy from the repository root (do not set Root Directory to `backend` unless you use backend/main.py)."
    )
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.main import app  # noqa: E402

__all__ = ["app"]
