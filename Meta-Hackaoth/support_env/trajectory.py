from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def default_trajectory_path() -> Path:
    root = Path(os.getenv("TRAJECTORY_LOG_DIR", "runs"))
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / f"trajectory_{stamp}.jsonl"


class TrajectoryLogger:
    """Append-only JSONL episode log (one object per line)."""

    def __init__(self, path: Optional[Path | str] = None) -> None:
        self.path = Path(path) if path else default_trajectory_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, row: Dict[str, Any]) -> None:
        line = json.dumps(row, default=str, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
