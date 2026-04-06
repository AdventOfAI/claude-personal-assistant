"""Shim so both `main:app` and `index:app` resolve (Vercel accepts several names)."""
from main import app

__all__ = ["app"]
