"""
Vercel build: copy frontend assets into public/ (served by the CDN).
Run via [tool.vercel.scripts] in pyproject.toml.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    src = root / "frontend"
    dst = root / "public"
    if not src.is_dir():
        print("build: no frontend/ directory; skipping public/")
        return
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.is_file():
            shutil.copy2(p, dst / p.name)
            print(f"build: copied {p.name} -> public/")
    print("build: done")


if __name__ == "__main__":
    main()
