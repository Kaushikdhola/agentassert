"""Generic adapter for framework-agnostic agent execution."""

from __future__ import annotations

import inspect
from typing import Any

from agentassert.adapters.base import BaseAdapter
from agentassert.trace.tracer import AgentTrace, AgentTracer


class GenericAdapter(BaseAdapter):
    """
    Generic adapter that runs plain callables or objects with a `run` method.

    This adapter is framework-agnostic and intentionally minimal for v0.1.0.
    LLM client patching/interception will be layered in later phases.
    """

    def __init__(self, tracer: AgentTracer) -> None:
        """Initialize adapter with the tracer that should receive events."""
        self._tracer = tracer

    def wrap_agent(self, agent: Any) -> Any:
        """Return the agent unchanged for the generic adapter."""
        return agent

    def run_agent(self, agent: Any, input: Any, **kwargs: Any) -> Any:
        """
        Execute the agent with the provided input.

        Supported forms:
        - Callable function: `agent(input, **kwargs)`
        - Object method: `agent.run(input, **kwargs)`
        """
        if hasattr(agent, "run") and callable(agent.run):
            return _invoke_with_supported_kwargs(agent.run, input, kwargs)

        if callable(agent):
            return _invoke_with_supported_kwargs(agent, input, kwargs)

        raise TypeError(
            "Expected agent to be callable or expose a callable `.run(...)` method, "
            f"actual type={type(agent).__name__!r}."
        )

    def extract_trace(self) -> AgentTrace:
        """Return the current trace from the tracer."""
        return self._tracer.get_trace()

    def inject_mock_tools(self, agent: Any, tools: list[Any]) -> Any:
        """
        Inject mock tools into an agent when possible.

        Generic behavior:
        - If the agent has a mutable `tools` attribute, replace matching tools by name.
        - Otherwise, leave the agent unchanged. In that case, callers can still pass
          tools through `run_agent(..., tools=[...])` if the callable accepts it.
        """
        if not tools:
            return agent

        if not hasattr(agent, "tools"):
            return agent

        current_tools = getattr(agent, "tools")
        if not isinstance(current_tools, list):
            return agent

        replacement_map: dict[str, Any] = {}
        for tool in tools:
            name = getattr(tool, "name", None)
            if isinstance(name, str):
                replacement_map[name] = tool

        replaced: list[Any] = []
        for current in current_tools:
            current_name = getattr(current, "name", None)
            if isinstance(current_name, str) and current_name in replacement_map:
                replaced.append(replacement_map[current_name])
            else:
                replaced.append(current)

        setattr(agent, "tools", replaced)
        return agent


def _invoke_with_supported_kwargs(callable_obj: Any, input_value: Any, kwargs: dict[str, Any]) -> Any:
    """Call a function with only keyword arguments it accepts."""
    signature = inspect.signature(callable_obj)
    accepts_var_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )

    if accepts_var_kwargs:
        return callable_obj(input_value, **kwargs)

    accepted_names = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    filtered_kwargs = {key: value for key, value in kwargs.items() if key in accepted_names}
    return callable_obj(input_value, **filtered_kwargs)
