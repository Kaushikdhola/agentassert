"""Test item representation for AgentAssert."""

from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from agentassert.core.outcome import Outcome


class TestItem(BaseModel):
    """
    Represents a single test item discovered by the collector.

    A TestItem wraps a test function decorated with @agent_test and contains
    all metadata needed to execute and report on the test.

    Attributes:
        name: The name of the test function.
        function: The actual test function to execute.
        file_path: Path to the file containing the test.
        line_number: Line number where the test function is defined.
        module_name: The module name (e.g., 'tests.test_agent').
        markers: List of marker names applied to this test (e.g., ['slow', 'integration']).
        scenario_index: If this is a parametrized scenario, the index (0-based).
        scenario_name: If this is a parametrized scenario, the scenario name.
        outcome: The outcome after execution (None until test is run).
    """

    name: str
    function: Callable[..., Any] = Field(exclude=True)
    file_path: Path
    line_number: int
    module_name: str
    markers: list[str] = Field(default_factory=list)
    scenario_index: int | None = None
    scenario_name: str | None = None
    outcome: Outcome | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def node_id(self) -> str:
        """
        Return a unique identifier for this test item.

        Format: module_name::function_name::scenario_index (if applicable)
        Example: tests.test_agent::test_calls_search::0
        """
        base_id = f"{self.module_name}::{self.name}"
        if self.scenario_index is not None:
            base_id = f"{base_id}::{self.scenario_index}"
        return base_id

    @property
    def short_name(self) -> str:
        """Return a short display name for the test."""
        if self.scenario_name:
            return f"{self.name}[{self.scenario_name}]"
        if self.scenario_index is not None:
            return f"{self.name}[{self.scenario_index}]"
        return self.name

    @property
    def location(self) -> str:
        """Return a human-readable location string."""
        return f"{self.file_path}:{self.line_number}"

    def set_outcome(self, outcome: Outcome) -> None:
        """Set the outcome for this test item."""
        self.outcome = outcome
