"""
Machine DSL — define states, transitions, and guards.

Usage::

    from railyard import Machine, state

    m = Machine(start='draft')
    m.add(state('draft', tools=['write', 'edit']))
    m.add(state('review', tools=['comment', 'approve']))
    m.add(state('done', terminal=True))
    m.allow('draft -> review')
    m.allow('review -> done', guard=lambda ctx: ctx.get('approved'))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from railyard.runtime import Session

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def state(
    name: str,
    *,
    tools: Optional[List[str]] = None,
    terminal: bool = False,
) -> "State":
    """Convenience factory for creating a :class:`State`."""
    return State(name=name, tools=tools or [], terminal=terminal)


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass
class State:
    """A single node in the state machine."""

    name: str
    tools: List[str] = field(default_factory=list)
    terminal: bool = False

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self.name == other.name
        return NotImplemented


@dataclass
class Transition:
    """An edge between two states, optionally guarded."""

    from_state: str
    to_state: str
    guard: Optional[Callable[[Dict[str, Any]], bool]] = None

    def is_allowed(self, context: Dict[str, Any]) -> bool:
        """Return *True* if the guard passes (or no guard is set)."""
        if self.guard is None:
            return True
        try:
            return bool(self.guard(context))
        except Exception:
            return False

    def __repr__(self) -> str:
        guard_label = "guarded" if self.guard else "open"
        return f"Transition({self.from_state!r} -> {self.to_state!r}, {guard_label})"


# ---------------------------------------------------------------------------
# Machine
# ---------------------------------------------------------------------------


class MachineError(Exception):
    """Base exception for machine definition errors."""


class Machine:
    """
    A finite-state machine that constrains an agent's workflow.

    Parameters
    ----------
    start : str
        Name of the initial state.
    """

    def __init__(self, start: str) -> None:
        self._start: str = start
        self._states: Dict[str, State] = {}
        self._transitions: Dict[str, List[Transition]] = {}  # keyed by from_state

    # -- builder API --------------------------------------------------------

    def add(self, st: State) -> "Machine":
        """Register a state.  Returns *self* for chaining."""
        if st.name in self._states:
            raise MachineError(f"Duplicate state: {st.name!r}")
        self._states[st.name] = st
        self._transitions.setdefault(st.name, [])
        return self

    def allow(
        self,
        spec: str,
        *,
        guard: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> "Machine":
        """
        Declare a legal transition.

        *spec* is ``'state_a -> state_b'``.

        *guard* is an optional callable ``(context) -> bool`` that must
        return *True* for the transition to proceed at runtime.
        """
        parts = [p.strip() for p in spec.split("->")]
        if len(parts) != 2 or not all(parts):
            raise MachineError(f"Bad transition spec: {spec!r}")
        from_name, to_name = parts
        if from_name not in self._states:
            raise MachineError(f"Unknown state: {from_name!r}")
        if to_name not in self._states:
            raise MachineError(f"Unknown state: {to_name!r}")
        t = Transition(from_state=from_name, to_state=to_name, guard=guard)
        self._transitions[from_name].append(t)
        return self

    # -- queries ------------------------------------------------------------

    @property
    def start_state(self) -> str:
        """Name of the start state."""
        return self._start

    def get_state(self, name: str) -> State:
        return self._states[name]

    def get_allowed_tools(self, state_name: str) -> List[str]:
        """Return tool names permitted in *state_name*."""
        return list(self._states[state_name].tools)

    def get_transitions(self, from_state: str) -> List[Transition]:
        """Return all transitions originating from *from_state*."""
        return list(self._transitions.get(from_state, []))

    def get_transition(self, from_state: str, to_state: str) -> Optional[Transition]:
        """Return the specific transition, or *None*."""
        for t in self._transitions.get(from_state, []):
            if t.to_state == to_state:
                return t
        return None

    @property
    def states(self) -> List[State]:
        return list(self._states.values())

    @property
    def state_names(self) -> List[str]:
        return list(self._states.keys())

    # -- validation ---------------------------------------------------------

    def validate(self) -> None:
        """
        Check the machine is well-formed.

        Raises :class:`MachineError` if:
        * the start state does not exist
        * any state is unreachable from the start state
        * a non-terminal state has no outgoing transitions (dead end)
        """
        if self._start not in self._states:
            raise MachineError(f"Start state {self._start!r} not registered")

        # BFS reachability
        visited: Set[str] = set()
        queue = [self._start]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for t in self._transitions.get(current, []):
                queue.append(t.to_state)

        unreachable = set(self._states) - visited
        if unreachable:
            raise MachineError(f"Unreachable states: {unreachable}")

        # dead-end check
        for name, st in self._states.items():
            if not st.terminal and not self._transitions.get(name):
                raise MachineError(
                    f"Non-terminal state {name!r} has no outgoing transitions"
                )

    # -- runtime entry point ------------------------------------------------

    def run(self, agent_fn: "Callable") -> Session:
        """
        Create a :class:`Session` for running the agent through the machine.

        Usage::

            with m.run(agent) as session:
                session.step()
        """
        from railyard.runtime import Runtime

        rt = Runtime(self)
        return rt.session(agent_fn)
