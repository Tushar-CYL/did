"""Atomic JSON persistence. Writes are fresh each run (callers overwrite)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .. import config


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # atomic: write to temp in same dir, then replace
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def raw_path(slug: str, kind: str) -> Path:
    """kind = 'hiring' | 'news'."""
    return config.RAW_DIR / slug / f"{kind}.json"


def normalized_path() -> Path:
    return config.NORMALIZED_DIR / "companies.json"
