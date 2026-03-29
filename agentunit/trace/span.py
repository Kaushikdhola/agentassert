"""Span representation for grouping related execution events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agentunit.trace.event import Event, EventType


class Span(BaseModel):
    """
    A span groups related events in an agent execution.

    Spans provide a hierarchical view of execution, where a parent span
    (e.g., an agent run) contains child spans (e.g., individual tool calls).

    Attributes:
        span_id: Unique identifier for this span.
        name: Human-readable name for the span.
        parent_id: ID of the parent span, if any.
        events: List of events that occurred within this span.
        start_time: When the span started.
        end_time: When the span ended.
        metadata: Additional span-specific metadata.
    """

    span_id: str
    name: str
    parent_id: str | None = None
    events: list[Event] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def add_event(self, event: Event) -> None:
        """Add an event to this span."""
        self.events.append(event)

    def close(self, end_time: datetime | None = None) -> None:
        """Close the span with the given end time."""
        self.end_time = end_time or datetime.utcnow()

    @property
    def duration_ms(self) -> int:
        """Return the duration of this span in milliseconds."""
        if self.end_time is None:
            return 0
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() * 1000)

    @property
    def event_count(self) -> int:
        """Return the number of events in this span."""
        return len(self.events)

    def get_events_by_type(self, event_type: EventType) -> list[Event]:
        """Return all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    @property
    def llm_calls(self) -> list[Event]:
        """Return all LLM call events."""
        return self.get_events_by_type(EventType.LLM_CALL)

    @property
    def tool_calls(self) -> list[Event]:
        """Return all tool call events."""
        return self.get_events_by_type(EventType.TOOL_CALL)
