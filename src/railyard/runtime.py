"""
Runtime — per-state tool gating and agent execution loop.

The runtime wraps an agent callable so that:

* only tools legal in the current state are exposed
* transitions are validated before execution
* every transition is logged
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Protocol

from railyard.log import TransitionLog

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidTransition(Exception):
    """Raised when the agent attempts a transition that is not allowed."""


# ---------------------------------------------------------------------------
# Agent protocol
# ---------------------------------------------------------------------------


class AgentAction:
    """
    What an agent returns from each step.

    Attributes
    ----------
    tool : str
        The tool the agent wants to call.
    next_state : str
        The state the agent wants to transition to.
    payload : dict
        Arbitrary data passed to the transition guard and logged.
    """

    def __init__(
        self,
        tool: str,
        next_state: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.tool = tool
        self.next_state = next_state
        self.payload: Dict[str, Any] = payload or {}

    def __repr__(self) -> str:
        return (
            f"AgentAction(tool={self.tool!r}, next_state={self.next_state!r}, "
            f"payload={self.payload!r})"
        )


# ---------------------------------------------------------------------------
# Session — context-manager returned by Machine.run()
# ---------------------------------------------------------------------------


class Session:
    """
    Manages a single run of an agent through a state machine.

    Use as a context manager::

        with machine.run(agent_fn) as session:
            session.step()
            session.step()
    """

    def __init__(self, runtime: "Runtime", agent_fn: Callable) -> None:
        self._runtime = runtime
        self._agent_fn = agent_fn
        self._finished = False

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    # -- execution ----------------------------------------------------------

    @property
    def current_state(self) -> str:
        return self._runtime.current_state

    @property
    def allowed_tools(self) -> List[str]:
        return self._runtime.allowed_tools

    @property
    def is_terminal(self) -> bool:
        return self._runtime.is_terminal

    def step(self, context: Optional[Dict[str, Any]] = None) -> AgentAction:
        """
        Ask the agent for its next action, then execute the transition.

        Returns the :class:`AgentAction` that was executed.

        Raises :class:`InvalidTransition` if the proposed transition is
        illegal or the tool is not allowed in the current state.
        """
        if self._finished:
            raise InvalidTransition("Session already finished (terminal state reached)")

        ctx = context or {}
        action = self._agent_fn(self._runtime, ctx)
        self._runtime.execute(action, ctx)
        if self._runtime.is_terminal:
            self._finished = True
        return action

    def run_until_done(self, context: Optional[Dict[str, Any]] = None) -> List[AgentAction]:
        """Run steps until a terminal state is reached."""
        actions: List[AgentAction] = []
        while not self._finished:
            actions.append(self.step(context))
        return actions


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


class Runtime:
    """
    Drives a :class:`~railyard.machine.Machine` forward step-by-step.

    Parameters
    ----------
    machine : Machine
        The state machine definition.
    """

    def __init__(self, machine: "Machine") -> None:  # noqa: F821 — forward ref
        self._machine = machine
        self._current: str = machine.start_state
        self._log = TransitionLog()

    # -- properties ---------------------------------------------------------

    @property
    def current_state(self) -> str:
        return self._current

    @property
    def allowed_tools(self) -> List[str]:
        return self._machine.get_allowed_tools(self._current)

    @property
    def is_terminal(self) -> bool:
        return self._machine.get_state(self._current).terminal

    @property
    def log(self) -> TransitionLog:
        return self._log

    # -- transition ---------------------------------------------------------

    def validate_transition(self, action: AgentAction, context: Dict[str, Any]) -> None:
        """
        Check that *action* is legal from the current state.

        Raises :class:`InvalidTransition` on violation.
        """
        # tool must be allowed
        allowed = self.allowed_tools
        if action.tool not in allowed:
            raise InvalidTransition(
                f"Tool {action.tool!r} not allowed in state {self._current!r}. "
                f"Allowed: {allowed}"
            )

        # transition must exist
        t = self._machine.get_transition(self._current, action.next_state)
        if t is None:
            valid = [
                tr.to_state
                for tr in self._machine.get_transitions(self._current)
            ]
            raise InvalidTransition(
                f"No transition from {self._current!r} to {action.next_state!r}. "
                f"Valid targets: {valid}"
            )

        # guard must pass
        if not t.is_allowed(context):
            raise InvalidTransition(
                f"Guard rejected transition {self._current!r} -> "
                f"{action.next_state!r}"
            )

    def execute(self, action: AgentAction, context: Dict[str, Any]) -> None:
        """Validate and perform the transition, logging it."""
        self.validate_transition(action, context)
        old = self._current
        self._current = action.next_state
        self._log.append(
            from_state=old,
            to_state=self._current,
            action=action.tool,
            context_snapshot=copy.deepcopy(context),
        )

    def session(self, agent_fn: Callable) -> Session:
        """Create a :class:`Session` for the given agent function."""
        return Session(self, agent_fn)
