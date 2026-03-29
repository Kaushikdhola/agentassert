"""MockTool implementation for stubbing agent tool calls."""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from agentassert.trace.tracer import AgentTracer

# Context variable to hold the active tracer during test execution
_active_tracer: ContextVar["AgentTracer | None"] = ContextVar("_active_tracer", default=None)


def get_active_tracer() -> "AgentTracer | None":
    return _active_tracer.get()


def set_active_tracer(tracer: "AgentTracer | None") -> None:
    _active_tracer.set(tracer)


@dataclass
class ToolCall:
    """Record of a single tool invocation."""

    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Exception | None = None


class MockTool:
    """
    Drop-in replacement for any agent tool.

    Intercepts calls and returns deterministic responses for testing.

    Args:
        name: The name of the tool being mocked.
        returns: Static value to return on every call.
        side_effect: Callable invoked with the tool's arguments to compute return value.
        raises: Exception instance to raise on every call.
        returns_fixture: Path to a JSON file containing the return value.
        returns_sequence: List of values to return in order; can include exceptions.
        latency_ms: Simulated latency in milliseconds (for future use).
        fail_after: Number of successful calls before raising an error.

    Example:
        >>> search = MockTool("web_search", returns={"results": ["item1"]})
        >>> result = search(query="AI news")
        >>> assert result == {"results": ["item1"]}
        >>> assert search.call_count == 1
    """

    def __init__(
        self,
        name: str,
        *,
        returns: Any = None,
        side_effect: Callable[..., Any] | None = None,
        raises: Exception | None = None,
        returns_fixture: str | None = None,
        returns_sequence: list[Any] | None = None,
        latency_ms: int = 0,
        fail_after: int | None = None,
    ) -> None:
        self.name = name
        self._returns = returns
        self._side_effect = side_effect
        self._raises = raises
        self._returns_fixture = returns_fixture
        self._returns_sequence = returns_sequence or []
        self._sequence_index = 0
        self._latency_ms = latency_ms
        self._fail_after = fail_after
        self._calls: list[ToolCall] = []
        self._fixture_data: Any = None

        # Load fixture data if specified
        if self._returns_fixture:
            self._load_fixture()

    def _load_fixture(self) -> None:
        fixture_path = Path(self._returns_fixture)
        if fixture_path.exists():
            with open(fixture_path, "r") as f:
                self._fixture_data = json.load(f)
        else:
            raise FileNotFoundError(f"Fixture file not found: {self._returns_fixture}")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the mock tool.

        Records the call to both internal history AND the active tracer.
        """
        call = ToolCall(args=args, kwargs=kwargs)
        start_time = time.time()

        try:
            result = self._compute_result(*args, **kwargs)
            call.result = result
            self._calls.append(call)
            
            # Record to active tracer if one exists
            latency_ms = int((time.time() - start_time) * 1000)
            self._record_to_tracer(kwargs, result, success=True, latency_ms=latency_ms)
            
            return result
        except Exception as e:
            call.error = e
            self._calls.append(call)
            
            # Record error to active tracer
            latency_ms = int((time.time() - start_time) * 1000)
            self._record_to_tracer(kwargs, None, success=False, error=str(e), latency_ms=latency_ms)
            
            raise

    def _record_to_tracer(
        self,
        input_kwargs: dict[str, Any],
        output: Any,
        success: bool,
        error: str | None = None,
        latency_ms: int = 0,
    ) -> None:
        tracer = get_active_tracer()
        if tracer is not None:
            tracer.record_tool_call(
                tool=self.name,
                input_data=input_kwargs,
                output=output,
                success=success,
                error=error,
                latency_ms=latency_ms,
            )

    def _compute_result(self, *args: Any, **kwargs: Any) -> Any:
        # Check fail_after
        if self._fail_after is not None and len(self._calls) >= self._fail_after:
            raise RuntimeError(f"MockTool '{self.name}' configured to fail after {self._fail_after} calls")

        # Priority 1: raises (always raises)
        if self._raises is not None:
            raise self._raises

        # Priority 2: returns_sequence (iterate through values)
        if self._returns_sequence:
            if self._sequence_index < len(self._returns_sequence):
                value = self._returns_sequence[self._sequence_index]
                self._sequence_index += 1
                if isinstance(value, Exception):
                    raise value
                return value
            # Exhausted sequence, return None
            return None

        # Priority 3: side_effect (dynamic return)
        if self._side_effect is not None:
            return self._side_effect(*args, **kwargs)

        # Priority 4: returns_fixture
        if self._fixture_data is not None:
            return self._fixture_data

        # Priority 5: static returns value
        return self._returns

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def calls(self) -> list[ToolCall]:
        return self._calls.copy()

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def last_call(self) -> ToolCall | None:
        return self._calls[-1] if self._calls else None

    def was_called_with(self, **kwargs: Any) -> bool:
        """
        Check if any call matched the specified kwargs.

        Args:
            **kwargs: Expected keyword arguments (supports matchers).

        Returns:
            True if at least one call matched.
        """
        for call in self._calls:
            if self._call_matches(call, kwargs):
                return True
        return False

    def nth_call_had(self, n: int, **kwargs: Any) -> bool:
        """
        Check if the nth call (0-indexed) had the specified kwargs.

        Args:
            n: Call index (0-based).
            **kwargs: Expected keyword arguments.

        Returns:
            True if the nth call matched.
        """
        if n < 0 or n >= len(self._calls):
            return False
        return self._call_matches(self._calls[n], kwargs)

    def _call_matches(self, call: ToolCall, expected: dict[str, Any]) -> bool:
        for key, expected_value in expected.items():
            actual_value = call.kwargs.get(key)
            if hasattr(expected_value, "matches") and callable(expected_value.matches):
                if not expected_value.matches(actual_value):
                    return False
            elif actual_value != expected_value:
                return False
        return True

    def reset(self) -> None:
        self._calls.clear()
        self._sequence_index = 0


class MockToolset:
    """
    A collection of MockTools for reuse across tests.

    Args:
        name: Optional name for the toolset.
        tools: List of MockTool instances.

    Example:
        >>> toolset = MockToolset(
        ...     name="research_tools",
        ...     tools=[
        ...         MockTool("web_search", returns={"results": []}),
        ...         MockTool("summarize", returns={"summary": "..."}),
        ...     ]
        ... )
    """

    def __init__(
        self,
        tools: list[MockTool],
        name: str = "",
    ) -> None:
        self.name = name
        self.tools = tools
        self._tool_map = {tool.name: tool for tool in tools}

    def get(self, tool_name: str) -> MockTool | None:
        """Get a tool by name."""
        return self._tool_map.get(tool_name)

    def __iter__(self):
        """Iterate over tools."""
        return iter(self.tools)

    def __len__(self) -> int:
        """Return number of tools in the set."""
        return len(self.tools)

    def reset_all(self) -> None:
        """Reset call history on all tools."""
        for tool in self.tools:
            tool.reset()


def mock_tool(
    name: str,
    *,
    returns: Any = None,
    side_effect: Callable[..., Any] | None = None,
    raises: Exception | None = None,
    returns_fixture: str | None = None,
    returns_sequence: list[Any] | None = None,
    latency_ms: int = 0,
    fail_after: int | None = None,
) -> MockTool:
    """
    Factory function to create a MockTool.

    This is the primary API for creating mock tools in tests.

    Args:
        name: The name of the tool being mocked.
        returns: Static value to return on every call.
        side_effect: Callable to compute dynamic return values.
        raises: Exception to raise on every call.
        returns_fixture: Path to JSON fixture file.
        returns_sequence: List of values to return in order.
        latency_ms: Simulated latency.
        fail_after: Fail after N successful calls.

    Returns:
        A configured MockTool instance.

    Example:
        >>> search = mock_tool("web_search", returns={"results": ["AI news"]})
        >>> bad_api = mock_tool("external_api", raises=ConnectionError("timeout"))
    """
    return MockTool(
        name=name,
        returns=returns,
        side_effect=side_effect,
        raises=raises,
        returns_fixture=returns_fixture,
        returns_sequence=returns_sequence,
        latency_ms=latency_ms,
        fail_after=fail_after,
    )
