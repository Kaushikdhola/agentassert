"""Built-in fixtures and the AgentHarness implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentunit.adapters.generic import GenericAdapter
from agentunit.mocks.tool_mock import set_active_tracer
from agentunit.trace.tracer import AgentTrace, AgentTracer


@dataclass
class AgentHarness:
    """
    Test harness responsible for running an agent under AgentUnit control.

    The harness initializes mocks, executes the agent via an adapter, captures
    the execution trace, and returns the resulting `AgentTrace`.
    """

    test_id: str = ""
    _last_trace: AgentTrace | None = field(default=None, repr=False)

    def run(
        self,
        agent: Any,
        input: Any,
        tools: list[Any] | None = None,
        toolset: Any | None = None,
        **kwargs: Any,
    ) -> AgentTrace:
        """
        Run an agent and return its captured trace.

        Args:
            agent: The target agent object or callable.
            input: Input payload passed to the agent.
            tools: Optional explicit list of mock tools.
            toolset: Optional toolset object that contains tools.
            **kwargs: Additional runtime kwargs passed to the agent.

        Returns:
            An `AgentTrace` with the execution outcome and events.
        """
        tracer = AgentTracer(test_id=self.test_id)
        adapter = GenericAdapter(tracer=tracer)

        prepared_tools = self._initialize_mocks(tools=tools, toolset=toolset)

        # Activate tracer context so MockTools record their calls
        set_active_tracer(tracer)

        try:
            with tracer:
                tracer.set_input(input)
                wrapped_agent = adapter.wrap_agent(agent)
                wrapped_agent = adapter.inject_mock_tools(wrapped_agent, prepared_tools)

                try:
                    output = adapter.run_agent(
                        wrapped_agent,
                        input,
                        tools=prepared_tools if prepared_tools else None,
                        **kwargs,
                    )
                    tracer.set_output(output)
                except Exception as exc:
                    tracer.set_failed(error=str(exc), exception_type=type(exc).__name__)
        finally:
            # Always clear the active tracer to avoid leaking state
            set_active_tracer(None)

        trace = adapter.extract_trace()
        self._last_trace = trace
        return trace

    def _initialize_mocks(self, tools: list[Any] | None, toolset: Any | None) -> list[Any]:
        """
        Normalize mock tool inputs from either `tools` or `toolset`.

        Returns:
            A list of mock tools to inject.
        """
        if tools:
            return tools

        if toolset is None:
            return []

        if hasattr(toolset, "tools") and isinstance(toolset.tools, list):
            return toolset.tools

        if isinstance(toolset, list):
            return toolset

        return []
