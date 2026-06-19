"""
Replay — re-execute a logged transition sequence against a machine to
verify it was valid.

Useful for auditing, debugging, and compliance checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from railyard.log import TransitionLog
from railyard.runtime import InvalidTransition


@dataclass
class ReplayResult:
    """Outcome of replaying a transition log."""

    valid: bool
    total_steps: int
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


class Replay:
    """
    Replay a :class:`TransitionLog` against a :class:`Machine`.

    Usage::

        result = Replay(machine).check(log)
        if not result:
            for err in result.errors:
                print(err)
    """

    def __init__(self, machine: "Machine") -> None:  # noqa: F821
        self._machine = machine

    def check(self, log: TransitionLog) -> ReplayResult:
        """
        Validate every entry in *log* against the machine.

        Returns a :class:`ReplayResult` with any mismatches.
        """
        errors: List[Dict[str, Any]] = []
        current = self._machine.start_state

        for idx, entry in enumerate(log):
            from_state = entry["from"]
            to_state = entry["to"]
            action = entry["action"]
            context = entry.get("context_snapshot", {})

            # verify the log's from_state matches where we think we are
            if from_state != current:
                errors.append(
                    {
                        "step": idx,
                        "type": "state_mismatch",
                        "message": (
                            f"Expected from_state={current!r}, got {from_state!r}"
                        ),
                        "entry": entry,
                    }
                )
                # try to continue from the log's own state
                current = from_state

            # check transition exists
            t = self._machine.get_transition(from_state, to_state)
            if t is None:
                errors.append(
                    {
                        "step": idx,
                        "type": "invalid_transition",
                        "message": (
                            f"No transition {from_state!r} -> {to_state!r}"
                        ),
                        "entry": entry,
                    }
                )
                current = to_state
                continue

            # check guard
            if not t.is_allowed(context):
                errors.append(
                    {
                        "step": idx,
                        "type": "guard_failed",
                        "message": (
                            f"Guard rejected {from_state!r} -> {to_state!r}"
                        ),
                        "entry": entry,
                    }
                )

            current = to_state

        return ReplayResult(
            valid=len(errors) == 0,
            total_steps=len(log),
            errors=errors,
        )
