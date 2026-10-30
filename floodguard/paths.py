"""Application resource and working-directory paths."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return a path to a bundled application resource."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def documents_directory() -> Path:
    """Return the user's documents directory with a sensible fallback."""
    documents = Path.home() / "Documents"
    if documents.is_dir():
        return documents
    return Path.home()


def studio_directory() -> Path:
    """Return the FloodGuard Studio working directory under Documents."""
    return documents_directory() / "FloodGuard Studio"


def projects_directory() -> Path:
    return studio_directory() / "Projects"


def reports_directory() -> Path:
    return studio_directory() / "Reports"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
