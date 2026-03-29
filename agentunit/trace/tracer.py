"""Agent tracer for capturing execution traces."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agentunit.trace.event import (
    Event,
    EventType,
    LLMCallEvent,
    ToolCallEvent,
)
from agentunit.trace.tree import ExecutionTree


class AgentTrace(BaseModel):
    """
    Captures the complete execution trace of an agent run.

    AgentTrace is the primary data structure returned by agent_harness.run().
    It contains all events (LLM calls, tool calls, etc.) that occurred during
    execution and provides methods for querying the trace.

    Matches the trace record format from Section 7 of the spec.

    Attributes:
        test_id: Unique identifier for the test that produced this trace.
        timestamp: When the trace was created.
        seed: Random seed for deterministic execution (default 42).
        agent_input: The input that was given to the agent.
        events: List of all events in execution order.
        final_output: The final output produced by the agent.
        started_at: When the agent execution started.
        ended_at: When the agent execution ended.
        outcome: The execution outcome ('completed', 'failed', 'timeout', etc.).
        error: Error message if execution failed.
        exception_type: Type of exception if execution failed.
        total_steps: Number of steps (LLM + tool calls) in the execution.
        total_tokens: Total tokens consumed across all LLM calls.
        total_cost_usd: Total cost in USD for the execution.
        metadata: Additional trace metadata.
    """

    test_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    seed: int = 42
    agent_input: Any = None
    events: list[Event] = Field(default_factory=list)
    final_output: Any = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    outcome: str = "pending"  # pending, completed, failed, timeout
    error: str | None = None
    exception_type: str | None = None
    total_steps: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def finalize(self) -> "AgentTrace":
        """
        Compute and store aggregate metrics from events.

        Call this after all events have been recorded to populate
        total_steps, total_tokens, and total_cost_usd fields.

        Returns:
            Self for chaining.
        """
        self.total_steps = sum(
            1 for e in self.events
            if e.event_type in (EventType.LLM_CALL, EventType.TOOL_CALL)
        )
        self.total_tokens = sum(
            e.total_tokens for e in self.events
            if isinstance(e, LLMCallEvent)
        )
        self.total_cost_usd = sum(
            e.cost_usd for e in self.events
            if isinstance(e, LLMCallEvent)
        )
        return self

    # Event access

    @property
    def step_count(self) -> int:
        if self.total_steps > 0:
            return self.total_steps
        return sum(
            1 for e in self.events
            if e.event_type in (EventType.LLM_CALL, EventType.TOOL_CALL)
        )

    @property
    def llm_call_count(self) -> int:
        return sum(1 for e in self.events if e.event_type == EventType.LLM_CALL)

    @property
    def tool_call_count(self) -> int:
        return sum(1 for e in self.events if e.event_type == EventType.TOOL_CALL)

    def get_tool_calls(self, tool_name: str | None = None) -> list[ToolCallEvent]:
        """
        Get all tool call events, optionally filtered by tool name.

        Args:
            tool_name: If provided, only return calls to this tool.

        Returns:
            List of ToolCallEvent objects.
        """
        tool_events = [
            e for e in self.events
            if e.event_type == EventType.TOOL_CALL and isinstance(e, ToolCallEvent)
        ]
        if tool_name:
            tool_events = [e for e in tool_events if e.tool == tool_name]
        return tool_events

    def get_llm_calls(self) -> list[LLMCallEvent]:
        return [
            e for e in self.events
            if e.event_type == EventType.LLM_CALL and isinstance(e, LLMCallEvent)
        ]

    def get_tool_names_called(self) -> list[str]:
        return [
            e.tool for e in self.events
            if e.event_type == EventType.TOOL_CALL and isinstance(e, ToolCallEvent)
        ]

    # Cost and token tracking

    def get_computed_tokens(self) -> int:
        return sum(
            e.total_tokens for e in self.events
            if isinstance(e, LLMCallEvent)
        )

    def get_computed_cost_usd(self) -> float:
        return sum(
            e.cost_usd for e in self.events
            if isinstance(e, LLMCallEvent)
        )

    @property
    def total_latency_ms(self) -> int:
        return sum(e.latency_ms for e in self.events)

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return self.total_latency_ms / 1000.0

    # Outcome checks

    @property
    def completed(self) -> bool:
        return self.outcome == "completed"

    @property
    def failed(self) -> bool:
        return self.outcome == "failed"

    # Tree representation

    def to_tree(self) -> ExecutionTree:
        """Build an execution tree from this trace."""
        input_str = str(self.agent_input) if self.agent_input else ""
        return ExecutionTree.from_events(self.events, input_str)


class AgentTracer:
    """
    Tracer that intercepts and records agent execution.

    AgentTracer patches LLM client calls at the Python object level to
    intercept all calls, regardless of which framework is being used.

    Usage:
        with AgentTracer() as tracer:
            result = agent.run(input)
        trace = tracer.get_trace()
    """

    # LLM client methods to intercept (expanded in Phase 2+)
    INTERCEPT_TARGETS: list[str] = [
        "openai.OpenAI.chat.completions.create",
        "anthropic.Anthropic.messages.create",
    ]

    def __init__(self, test_id: str = "") -> None:
        """
        Initialize the tracer.

        Args:
            test_id: Unique identifier for this trace.
        """
        self._test_id = test_id
        self._events: list[Event] = []
        self._seq = 0
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._agent_input: Any = None
        self._final_output: Any = None
        self._outcome = "pending"
        self._error: str | None = None
        self._exception_type: str | None = None
        self._patches: list[Any] = []

    def __enter__(self) -> "AgentTracer":
        self._started_at = datetime.utcnow()
        # Note: Actual patching is implemented in GenericAdapter
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._ended_at = datetime.utcnow()
        if exc_type is not None:
            self._outcome = "failed"
            self._error = str(exc_val)
            self._exception_type = exc_type.__name__ if exc_type else None
        elif self._outcome == "pending":
            self._outcome = "completed"

    def record_llm_call(
        self,
        model: str,
        messages: list[dict[str, Any]],
        response: dict[str, Any],
        latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> LLMCallEvent:
        event = LLMCallEvent(
            seq=self._seq,
            model=model,
            messages=messages,
            response=response,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
        )
        self._events.append(event)
        self._seq += 1
        return event

    def record_tool_call(
        self,
        tool: str,
        input_data: dict[str, Any],
        output: Any,
        success: bool = True,
        error: str | None = None,
        latency_ms: int = 0,
    ) -> ToolCallEvent:
        event = ToolCallEvent(
            seq=self._seq,
            tool=tool,
            input=input_data,
            output=output,
            success=success,
            error=error,
            latency_ms=latency_ms,
        )
        self._events.append(event)
        self._seq += 1
        return event

    def set_input(self, agent_input: Any) -> None:
        self._agent_input = agent_input

    def set_output(self, output: Any) -> None:
        self._final_output = output
        if self._outcome == "pending":
            self._outcome = "completed"

    def set_failed(self, error: str, exception_type: str | None = None) -> None:
        self._outcome = "failed"
        self._error = error
        self._exception_type = exception_type

    def get_trace(self) -> AgentTrace:
        """
        Build and return the complete AgentTrace.

        Returns:
            AgentTrace containing all recorded events.
        """
        trace = AgentTrace(
            test_id=self._test_id,
            agent_input=self._agent_input,
            events=self._events.copy(),
            final_output=self._final_output,
            started_at=self._started_at,
            ended_at=self._ended_at or datetime.utcnow(),
            outcome=self._outcome,
            error=self._error,
            exception_type=self._exception_type,
        )
        return trace.finalize()
