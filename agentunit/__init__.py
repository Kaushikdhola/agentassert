"""
AgentUnit — Behavioral testing framework for AI agents.

AgentUnit is the missing test runner for AI agents — framework-agnostic,
locally executable, and built for CI/CD pipelines.

Example usage:
    import agentunit as au
    from agentunit import agent_test, expect, mock_tool

    @agent_test
    def test_research_agent_calls_search(agent_harness):
        search = mock_tool("web_search", returns={"results": ["AI news"]})

        trace = agent_harness.run(
            agent=my_agent,
            input="Find AI news",
            tools=[search]
        )

        expect(trace).tool("web_search").was_called()
        expect(trace).completed_within_steps(10)
"""

from agentunit._version import __version__, __version_info__

# Decorators
from agentunit.decorators import agent_test, fixture, scenario, scenarios

# Fluent assertions
from agentunit.assertions.fluent import expect

# Mocks
from agentunit.mocks.tool_mock import mock_tool, MockTool, MockToolset

# Matchers (for called_with assertions)
from agentunit.assertions.matchers import (
    contains,
    matches,
    starts_with,
    ends_with,
    any_string,
    greater_than,
    less_than,
    between,
    has_key,
    has_length,
    contains_item,
    is_type,
    is_not_none,
    is_none,
    anything,
    all_of,
    any_of,
    not_,
)

# Core types for type hints
from agentunit.trace.tracer import AgentTrace
from agentunit.core.outcome import Outcome, OutcomeStatus
from agentunit.fixtures import AgentHarness

__all__ = [
    # Version
    "__version__",
    "__version_info__",
    # Decorators
    "agent_test",
    "fixture",
    "scenario",
    "scenarios",
    # Assertions
    "expect",
    # Mocks
    "mock_tool",
    "MockTool",
    "MockToolset",
    # Matchers
    "contains",
    "matches",
    "starts_with",
    "ends_with",
    "any_string",
    "greater_than",
    "less_than",
    "between",
    "has_key",
    "has_length",
    "contains_item",
    "is_type",
    "is_not_none",
    "is_none",
    "anything",
    "all_of",
    "any_of",
    "not_",
    # Core types
    "AgentTrace",
    "AgentHarness",
    "Outcome",
    "OutcomeStatus",
]
