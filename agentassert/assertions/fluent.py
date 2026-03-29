"""Fluent assertion API for AgentAssert.

The expect() function is the primary entry point for all assertions.

Example:
    >>> trace = agent_harness.run(agent=my_agent, input="Do the task")
    >>> expect(trace).tool("web_search").was_called()
    >>> expect(trace).completed_within_steps(10)
    >>> expect(trace).output.not_empty()
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from agentassert.assertions.behavior import ToolAssertion, TraceAssertion

if TYPE_CHECKING:
    from agentassert.trace.tracer import AgentTrace


class OutputAssertion:
    """Assertions for agent output content."""

    def __init__(self, trace: AgentTrace) -> None:
        self._trace = trace

    def not_empty(self) -> "OutputAssertion":
        """Assert the output is not None or empty."""
        output = self._trace.final_output
        if output is None:
            raise AssertionError("Expected output to not be empty, actual output=None.")
        if isinstance(output, str) and output.strip() == "":
            raise AssertionError("Expected output to not be empty, actual output=''.")
        if isinstance(output, (list, dict)) and len(output) == 0:
            raise AssertionError(f"Expected output to not be empty, actual output={output!r}.")
        return self

    def contains(self, substring: str) -> "OutputAssertion":
        """Assert the output contains a substring."""
        output = self._trace.final_output
        output_str = str(output) if output is not None else ""
        if substring not in output_str:
            raise AssertionError(
                f"Expected output to contain {substring!r}, "
                f"actual output={output_str[:200]!r}{'...' if len(output_str) > 200 else ''}."
            )
        return self

    def does_not_contain(self, substring: str) -> "OutputAssertion":
        """Assert the output does not contain a substring."""
        output = self._trace.final_output
        output_str = str(output) if output is not None else ""
        if substring in output_str:
            raise AssertionError(
                f"Expected output to NOT contain {substring!r}, but it was found in output."
            )
        return self

    def is_valid_json(self) -> "OutputAssertion":
        """Assert the output is valid JSON."""
        output = self._trace.final_output
        if output is None:
            raise AssertionError("Expected output to be valid JSON, actual output=None.")
        if isinstance(output, (dict, list)):
            # Already a parsed structure
            return self
        if isinstance(output, str):
            try:
                json.loads(output)
            except json.JSONDecodeError as e:
                raise AssertionError(f"Expected output to be valid JSON, parse error: {e}.")
        else:
            raise AssertionError(
                f"Expected output to be valid JSON, actual type={type(output).__name__}."
            )
        return self

    def matches_schema(self, schema: type) -> "OutputAssertion":
        """Assert the output matches a Pydantic schema."""
        output = self._trace.final_output
        try:
            if hasattr(schema, "model_validate"):
                # Pydantic v2
                schema.model_validate(output)
            elif hasattr(schema, "parse_obj"):
                # Pydantic v1
                schema.parse_obj(output)
            else:
                raise AssertionError(f"Schema {schema} is not a Pydantic model.")
        except Exception as e:
            raise AssertionError(f"Output does not match schema {schema.__name__}: {e}.")
        return self

    def length_between(self, min_len: int, max_len: int) -> "OutputAssertion":
        """Assert the output length is between min and max (inclusive)."""
        output = self._trace.final_output
        output_str = str(output) if output is not None else ""
        actual_len = len(output_str)
        if not (min_len <= actual_len <= max_len):
            raise AssertionError(
                f"Expected output length between {min_len} and {max_len}, actual length={actual_len}."
            )
        return self


class ExpectTrace:
    """
    Fluent assertion builder for AgentTrace.

    This is the object returned by expect(trace).
    """

    def __init__(self, trace: AgentTrace) -> None:
        self._trace = trace
        self._trace_assertion = TraceAssertion(_trace=trace)

    def tool(self, tool_name: str) -> ToolAssertion:
        """Select a tool for assertions."""
        return ToolAssertion(_trace=self._trace, _tool_name=tool_name)

    @property
    def output(self) -> OutputAssertion:
        """Access output assertions."""
        return OutputAssertion(self._trace)

    # ── Delegate trace-level assertions ───────────────────────────

    def completed(self) -> "ExpectTrace":
        """Assert the agent completed successfully."""
        self._trace_assertion.completed()
        return self

    def completed_within_steps(self, n: int) -> "ExpectTrace":
        """Assert the agent completed in n or fewer steps."""
        self._trace_assertion.completed_within_steps(n)
        return self

    def took_at_least_steps(self, n: int) -> "ExpectTrace":
        """Assert the agent took at least n steps."""
        self._trace_assertion.took_at_least_steps(n)
        return self

    def failed(self) -> "ExpectTrace":
        """Assert the agent failed."""
        if not self._trace.failed:
            raise AssertionError(
                f"Expected trace outcome='failed', actual outcome={self._trace.outcome!r}."
            )
        return self

    def failed_gracefully(self) -> "ExpectTrace":
        """Assert the agent failed with a proper error, not an unhandled crash."""
        if self._trace.outcome != "failed":
            raise AssertionError(
                f"Expected trace outcome='failed', actual outcome={self._trace.outcome!r}."
            )
        # A graceful failure has an error message
        if self._trace.error is None:
            raise AssertionError(
                "Expected a graceful failure with an error message, but error=None."
            )
        return self

    def raised(self, exception_type: type) -> "ExpectTrace":
        """Assert the agent raised a specific exception type."""
        expected_name = exception_type.__name__
        actual_name = self._trace.exception_type
        if actual_name != expected_name:
            raise AssertionError(
                f"Expected exception type {expected_name!r}, actual={actual_name!r}."
            )
        return self

    def did_not_loop(self, window: int = 3) -> "ExpectTrace":
        """Assert the agent did not repeat the same tool sequence within a window."""
        tool_names = self._trace.get_tool_names_called()
        if len(tool_names) < window * 2:
            return self  # Not enough calls to detect a loop

        for i in range(len(tool_names) - window):
            pattern = tool_names[i : i + window]
            rest = tool_names[i + window :]
            for j in range(len(rest) - window + 1):
                if rest[j : j + window] == pattern:
                    raise AssertionError(
                        f"Detected repeated tool sequence {pattern!r} at positions {i} and {i + window + j}."
                    )
        return self


def expect(trace: AgentTrace) -> ExpectTrace:
    """
    Create a fluent assertion builder for an AgentTrace.

    This is the primary entry point for all AgentAssert assertions.

    Args:
        trace: The AgentTrace to make assertions against.

    Returns:
        An ExpectTrace instance for chaining assertions.

    Example:
        >>> expect(trace).tool("web_search").was_called()
        >>> expect(trace).completed_within_steps(10)
        >>> expect(trace).output.not_empty()
    """
    return ExpectTrace(trace)
