"""
Abstract adapter — wraps an agent so only tools legal in the current
state are exposed.

Subclass :class:`BaseAdapter` to integrate with a specific framework
(LangChain, CrewAI, custom, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List

from railyard.runtime import Runtime


class BaseAdapter(ABC):
    """
    Base class for framework adapters.

    An adapter is responsible for:

    1. Taking a full tool registry and the :class:`Runtime`.
    2. Returning only the tools allowed in the current state to the agent.
    3. Translating the agent's output into an :class:`AgentAction`.
    """

    def __init__(
        self,
        runtime: Runtime,
        tool_registry: Dict[str, Callable],
    ) -> None:
        self._runtime = runtime
        self._tool_registry = tool_registry

    @property
    def allowed_tool_names(self) -> List[str]:
        """Tool names permitted in the current state."""
        return self._runtime.allowed_tools

    def get_allowed_tools(self) -> Dict[str, Callable]:
        """Return the callable objects for tools allowed now."""
        return {
            name: self._tool_registry[name]
            for name in self.allowed_tool_names
            if name in self._tool_registry
        }

    @abstractmethod
    def invoke(self, prompt: str, context: Dict[str, Any]) -> Any:
        """
        Call the underlying agent/framework with only the allowed tools.

        Must return or internally produce an :class:`AgentAction` and
        pass it to ``self._runtime.execute(action, context)``.
        """
        ...
