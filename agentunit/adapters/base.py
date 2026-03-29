"""Base adapter interface for framework integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentunit.trace.tracer import AgentTrace


class BaseAdapter(ABC):
    """
    Base interface for framework adapters.

    Adapters bridge AgentUnit's generic harness and tracer with framework-specific
    execution models.
    """

    @abstractmethod
    def wrap_agent(self, agent: Any) -> Any:
        """Wrap an agent object with adapter-specific instrumentation."""

    @abstractmethod
    def run_agent(self, agent: Any, input: Any, **kwargs: Any) -> Any:
        """Execute the agent and return its output."""

    @abstractmethod
    def extract_trace(self) -> AgentTrace:
        """Extract and return the execution trace."""

    @abstractmethod
    def inject_mock_tools(self, agent: Any, tools: list[Any]) -> Any:
        """Replace real tools with mock tools on the given agent object."""
