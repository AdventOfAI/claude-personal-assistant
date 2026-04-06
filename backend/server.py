"""
Alternate Vercel entry: use with pyproject `[project.scripts] app = "backend.server:app"`.
Requires repo root on PYTHONPATH and `backend` as a package.
"""
from __future__ import annotations

import sys
from pathlib import Path

# `app` package lives under backend/
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.main import app  # noqa: E402

__all__ = ["app"]
