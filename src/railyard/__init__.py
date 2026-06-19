"""
Railyard — State-machine guardrails for AI agents.

Make illegal transitions impossible, not merely discouraged.
"""

from railyard.machine import Machine, State, Transition, state
from railyard.runtime import Runtime, Session, InvalidTransition, AgentAction
from railyard.log import TransitionLog
from railyard.replay import Replay, ReplayResult

__all__ = [
    "Machine",
    "State",
    "Transition",
    "state",
    "Runtime",
    "Session",
    "InvalidTransition",
    "AgentAction",
    "TransitionLog",
    "Replay",
    "ReplayResult",
]

__version__ = "0.1.0"
