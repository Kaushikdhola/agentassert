"""Event types for agent execution tracing."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can occur during agent execution."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    ERROR = "error"
    DECISION = "decision"


class Event(BaseModel):
    """
    Base class for all execution events.

    An Event represents a single action or decision during agent execution,
    such as an LLM call, tool invocation, or error.

    Attributes:
        seq: Sequence number (0-indexed) indicating order in the trace.
        event_type: The type of event.
        timestamp: When the event occurred.
        latency_ms: How long the event took in milliseconds.
        metadata: Additional event-specific metadata.
    """

    seq: int
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class LLMCallEvent(Event):
    """
    Event representing an LLM API call.

    Attributes:
        model: The model identifier (e.g., 'gpt-4o', 'claude-3-opus').
        messages: The messages sent to the LLM.
        response: The response content from the LLM.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total tokens (prompt + completion).
        cost_usd: Cost of this LLM call in USD.
    """

    event_type: EventType = EventType.LLM_CALL
    model: str = ""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    response: dict[str, Any] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def response_content(self) -> str:
        """Extract the text content from the response."""
        if isinstance(self.response, dict):
            # Handle OpenAI-style response
            if "content" in self.response:
                return str(self.response["content"])
            # Handle nested choices structure
            choices = self.response.get("choices", [])
            if choices and isinstance(choices[0], dict):
                message = choices[0].get("message", {})
                return str(message.get("content", ""))
        return str(self.response)


class ToolCallEvent(Event):
    """
    Event representing a tool invocation.

    Attributes:
        tool: The name of the tool that was called.
        input: The input/arguments passed to the tool.
        output: The output/result returned by the tool.
        success: Whether the tool call succeeded.
        error: Error message if the tool call failed.
    """

    event_type: EventType = EventType.TOOL_CALL
    tool: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    success: bool = True
    error: str | None = None

    @property
    def failed(self) -> bool:
        """Return True if this tool call failed."""
        return not self.success
