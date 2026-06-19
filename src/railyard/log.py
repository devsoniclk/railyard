"""
Transition log — JSONL audit trail of every state change.

Each entry::

    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "from": "draft",
        "to": "review",
        "action": "submit",
        "context_snapshot": {"author": "alice"}
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class TransitionLog:
    """Append-only log of transitions, serialisable to JSONL."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def append(
        self,
        *,
        from_state: str,
        to_state: str,
        action: str,
        context_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a transition."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": from_state,
            "to": to_state,
            "action": action,
            "context_snapshot": context_snapshot or {},
        }
        self._entries.append(entry)

    def get_history(self) -> List[Dict[str, Any]]:
        """Return a copy of the full history."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    # -- persistence --------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Write the log to *path* as JSONL."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as f:
            for entry in self._entries:
                f.write(json.dumps(entry) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "TransitionLog":
        """Load a log from a JSONL file."""
        log = cls()
        p = Path(path)
        if not p.exists():
            return log
        with p.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    log._entries.append(json.loads(line))
        return log
