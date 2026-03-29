"""Behavioral assertions for agent execution traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentassert.trace.event import ToolCallEvent
from agentassert.trace.tracer import AgentTrace


@dataclass
class CallAssertion:
    """Assertions scoped to a single tool call instance."""

    _tool_name: str
    _index: int
    _call: ToolCallEvent

    def had_input(self, **kwargs: Any) -> "CallAssertion":
        """
        Assert the selected call had the specified input arguments.

        Args:
            **kwargs: Expected key/value input pairs.

        Returns:
            The same CallAssertion for chaining.

        Raises:
            AssertionError: If any expected key/value does not match.
        """
        for key, expected in kwargs.items():
            actual = self._call.input.get(key)
            if not _value_matches(expected, actual):
                raise AssertionError(
                    f"Expected {self._tool_name} call #{self._index} input[{key!r}] to match {expected!r}, "
                    f"actual={actual!r}."
                )
        return self


@dataclass
class ToolAssertion:
    """Assertions for a specific tool inside an AgentTrace."""

    _trace: AgentTrace
    _tool_name: str

    def was_called(self) -> "ToolAssertion":
        """Assert the tool was called at least once."""
        actual = len(self._calls())
        if actual < 1:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called at least once, actual call_count={actual}."
            )
        return self

    def was_not_called(self) -> "ToolAssertion":
        """Assert the tool was never called."""
        actual = len(self._calls())
        if actual != 0:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to never be called, actual call_count={actual}."
            )
        return self

    def called_exactly(self, n: int) -> "ToolAssertion":
        """Assert the tool was called exactly n times."""
        actual = len(self._calls())
        if actual != n:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called exactly {n} times, actual={actual}."
            )
        return self

    def called_at_least(self, n: int) -> "ToolAssertion":
        """Assert the tool was called at least n times."""
        actual = len(self._calls())
        if actual < n:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called at least {n} times, actual={actual}."
            )
        return self

    def called_at_most(self, n: int) -> "ToolAssertion":
        """Assert the tool was called no more than n times."""
        actual = len(self._calls())
        if actual > n:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called at most {n} times, actual={actual}."
            )
        return self

    def called_before(self, other_tool: str) -> "ToolAssertion":
        """Assert this tool was called before another tool in the trace."""
        self_indices = _tool_indices(self._trace, self._tool_name)
        other_indices = _tool_indices(self._trace, other_tool)
        if not self_indices or not other_indices:
            raise AssertionError(
                f"Expected both tools to be called for ordering check: expected={self._tool_name!r} before "
                f"{other_tool!r}, actual calls={self._trace.get_tool_names_called()!r}."
            )
        if min(self_indices) > min(other_indices):
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called before {other_tool!r}, "
                f"actual first indices: {self._tool_name!r}={min(self_indices)}, {other_tool!r}={min(other_indices)}."
            )
        return self

    def called_after(self, other_tool: str) -> "ToolAssertion":
        """Assert this tool was called after another tool in the trace."""
        self_indices = _tool_indices(self._trace, self._tool_name)
        other_indices = _tool_indices(self._trace, other_tool)
        if not self_indices or not other_indices:
            raise AssertionError(
                f"Expected both tools to be called for ordering check: expected={self._tool_name!r} after "
                f"{other_tool!r}, actual calls={self._trace.get_tool_names_called()!r}."
            )
        if min(self_indices) < min(other_indices):
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called after {other_tool!r}, "
                f"actual first indices: {self._tool_name!r}={min(self_indices)}, {other_tool!r}={min(other_indices)}."
            )
        return self

    def called_with(self, **kwargs: Any) -> "ToolAssertion":
        """
        Assert at least one call to this tool had the specified kwargs.

        Values can be literals or matchers that expose a `matches(value) -> bool` method.
        """
        calls = self._calls()
        if not calls:
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to be called with {kwargs!r}, actual no calls were recorded."
            )

        for call in calls:
            if all(_value_matches(expected, call.input.get(key)) for key, expected in kwargs.items()):
                return self

        actual_inputs = [c.input for c in calls]
        raise AssertionError(
            f"Expected tool {self._tool_name!r} to be called with {kwargs!r}, actual inputs={actual_inputs!r}."
        )

    def nth_call(self, n: int) -> CallAssertion:
        """Select the nth call (0-indexed) for further assertions."""
        calls = self._calls()
        if n < 0 or n >= len(calls):
            raise AssertionError(
                f"Expected tool {self._tool_name!r} to have call index {n}, "
                f"actual call_count={len(calls)}."
            )
        return CallAssertion(_tool_name=self._tool_name, _index=n, _call=calls[n])

    def _calls(self) -> list[ToolCallEvent]:
        return self._trace.get_tool_calls(self._tool_name)


@dataclass
class TraceAssertion:
    """Assertions for global execution behavior of an AgentTrace."""

    _trace: AgentTrace

    def completed(self) -> "TraceAssertion":
        """Assert the agent reached terminal success state."""
        if not self._trace.completed:
            raise AssertionError(
                f"Expected trace outcome='completed', actual outcome={self._trace.outcome!r}."
            )
        return self

    def completed_within_steps(self, n: int) -> "TraceAssertion":
        """Assert the agent completed in n or fewer steps."""
        actual = self._trace.step_count
        if actual > n:
            raise AssertionError(
                f"Expected step_count <= {n}, actual step_count={actual}."
            )
        return self

    def took_at_least_steps(self, n: int) -> "TraceAssertion":
        """Assert the agent took at least n steps."""
        actual = self._trace.step_count
        if actual < n:
            raise AssertionError(
                f"Expected step_count >= {n}, actual step_count={actual}."
            )
        return self


def _tool_indices(trace: AgentTrace, tool_name: str) -> list[int]:
    positions: list[int] = []
    for idx, event in enumerate(trace.get_tool_calls()):
        if event.tool == tool_name:
            positions.append(idx)
    return positions


def _value_matches(expected: Any, actual: Any) -> bool:
    if hasattr(expected, "matches") and callable(expected.matches):
        return bool(expected.matches(actual))
    return expected == actual
