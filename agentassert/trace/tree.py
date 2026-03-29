"""Execution tree builder for visualizing agent traces."""

from typing import Any

from pydantic import BaseModel, Field

from agentassert.trace.event import Event, EventType, LLMCallEvent, ToolCallEvent
from agentassert.trace.span import Span


class TreeNode(BaseModel):
    """
    A node in the execution tree.

    Attributes:
        label: Display label for the node.
        event: The underlying event, if any.
        children: Child nodes.
        depth: Depth in the tree (0 = root).
    """

    label: str
    event: Event | None = None
    children: list["TreeNode"] = Field(default_factory=list)
    depth: int = 0

    model_config = {"arbitrary_types_allowed": True}

    def add_child(self, node: "TreeNode") -> None:
        """Add a child node."""
        node.depth = self.depth + 1
        self.children.append(node)


class ExecutionTree(BaseModel):
    """
    A tree representation of an agent's execution trace.

    The ExecutionTree provides a hierarchical view of the agent's execution,
    making it easy to visualize the sequence of LLM calls, tool invocations,
    and decisions.

    Attributes:
        root: The root node of the tree.
        spans: List of all spans in the execution.
    """

    root: TreeNode = Field(default_factory=lambda: TreeNode(label="Agent Execution"))
    spans: list[Span] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_events(cls, events: list[Event], agent_input: str = "") -> "ExecutionTree":
        """
        Build an execution tree from a list of events.

        Args:
            events: List of events in execution order.
            agent_input: The input that was given to the agent.

        Returns:
            An ExecutionTree representing the execution.
        """
        tree = cls()
        tree.root.label = f"Agent Execution: {agent_input[:50]}..." if len(agent_input) > 50 else f"Agent Execution: {agent_input}"

        for event in events:
            node = cls._event_to_node(event)
            tree.root.add_child(node)

        return tree

    @staticmethod
    def _event_to_node(event: Event) -> TreeNode:
        """Convert an event to a tree node."""
        if event.event_type == EventType.LLM_CALL:
            llm_event = event if isinstance(event, LLMCallEvent) else None
            if llm_event:
                content_preview = llm_event.response_content[:80]
                if len(llm_event.response_content) > 80:
                    content_preview += "..."
                label = f"[LLM] {llm_event.model}: {content_preview}"
            else:
                label = "[LLM] Call"
            return TreeNode(label=label, event=event)

        elif event.event_type == EventType.TOOL_CALL:
            tool_event = event if isinstance(event, ToolCallEvent) else None
            if tool_event:
                status = "✓" if tool_event.success else "✗"
                label = f"[TOOL] {tool_event.tool}({_format_input(tool_event.input)}) → {status}"
            else:
                label = "[TOOL] Call"
            return TreeNode(label=label, event=event)

        elif event.event_type == EventType.ERROR:
            label = f"[ERROR] {event.metadata.get('message', 'Unknown error')}"
            return TreeNode(label=label, event=event)

        else:
            label = f"[{event.event_type.value.upper()}]"
            return TreeNode(label=label, event=event)

    def render_text(self, indent: str = "  ") -> str:
        """
        Render the tree as a text string.

        Args:
            indent: The indentation string to use for each level.

        Returns:
            A string representation of the tree.
        """
        lines: list[str] = []
        self._render_node(self.root, lines, "", indent)
        return "\n".join(lines)

    def _render_node(
        self,
        node: TreeNode,
        lines: list[str],
        prefix: str,
        indent: str,
    ) -> None:
        """Recursively render a node and its children."""
        lines.append(f"{prefix}{node.label}")
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("└─ " if is_last else "├─ ")
            continuation = prefix + ("   " if is_last else "│  ")
            lines.append(f"{child_prefix}{child.label}")
            # Render grandchildren with proper continuation
            for j, grandchild in enumerate(child.children):
                gc_is_last = j == len(child.children) - 1
                gc_prefix = continuation + ("└─ " if gc_is_last else "├─ ")
                lines.append(f"{gc_prefix}{grandchild.label}")


def _format_input(input_dict: dict[str, Any], max_len: int = 50) -> str:
    """Format tool input for display."""
    if not input_dict:
        return ""
    parts = []
    for key, value in input_dict.items():
        val_str = str(value)
        if len(val_str) > 20:
            val_str = val_str[:17] + "..."
        parts.append(f"{key}={val_str}")
    result = ", ".join(parts)
    if len(result) > max_len:
        result = result[: max_len - 3] + "..."
    return result
