"""Test session management for AgentUnit."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentunit.core.item import TestItem
from agentunit.core.outcome import OutcomeStatus


class TestSession(BaseModel):
    """
    Represents a test session containing all discovered and executed tests.

    A TestSession is created when `agentunit run` is invoked and tracks
    all test items, fixtures, and aggregate statistics.

    Attributes:
        items: List of all discovered test items.
        fixtures: Dictionary mapping fixture names to their factory functions.
        config: Configuration options for this session.
        seed: Random seed for deterministic test ordering.
        start_time: Timestamp when the session started (set during run).
        end_time: Timestamp when the session ended (set after run).
    """

    items: list[TestItem] = Field(default_factory=list)
    fixtures: dict[str, Any] = Field(default_factory=dict, exclude=True)
    config: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None
    start_time: float | None = None
    end_time: float | None = None

    model_config = {"arbitrary_types_allowed": True}

    def add_item(self, item: TestItem) -> None:
        """Add a test item to the session."""
        self.items.append(item)

    def add_fixture(self, name: str, factory: Any) -> None:
        """Register a fixture factory function."""
        self.fixtures[name] = factory

    def get_fixture(self, name: str) -> Any | None:
        """Get a fixture factory by name."""
        return self.fixtures.get(name)

    @property
    def total_count(self) -> int:
        """Return total number of test items."""
        return len(self.items)

    @property
    def passed_count(self) -> int:
        """Return number of passed tests."""
        return sum(
            1 for item in self.items
            if item.outcome and item.outcome.status == OutcomeStatus.PASSED
        )

    @property
    def failed_count(self) -> int:
        """Return number of failed tests."""
        return sum(
            1 for item in self.items
            if item.outcome and item.outcome.status == OutcomeStatus.FAILED
        )

    @property
    def error_count(self) -> int:
        """Return number of errored tests."""
        return sum(
            1 for item in self.items
            if item.outcome and item.outcome.status == OutcomeStatus.ERROR
        )

    @property
    def skipped_count(self) -> int:
        """Return number of skipped tests."""
        return sum(
            1 for item in self.items
            if item.outcome and item.outcome.status == OutcomeStatus.SKIPPED
        )

    @property
    def total_duration_seconds(self) -> float:
        """Return total duration of all tests."""
        return sum(
            item.outcome.duration_seconds
            for item in self.items
            if item.outcome
        )

    @property
    def total_cost_usd(self) -> float:
        """Return total cost in USD across all tests."""
        return sum(
            item.outcome.total_cost_usd
            for item in self.items
            if item.outcome
        )

    @property
    def total_tokens(self) -> int:
        """Return total tokens consumed across all tests."""
        return sum(
            item.outcome.total_tokens
            for item in self.items
            if item.outcome
        )

    @property
    def all_passed(self) -> bool:
        """Return True if all tests passed (or were skipped)."""
        return all(
            item.outcome and item.outcome.is_success
            for item in self.items
        )

    def get_failed_items(self) -> list[TestItem]:
        """Return all failed or errored test items."""
        return [
            item for item in self.items
            if item.outcome and item.outcome.is_failure
        ]

    def items_by_file(self) -> dict[Path, list[TestItem]]:
        """Group test items by their source file."""
        result: dict[Path, list[TestItem]] = {}
        for item in self.items:
            if item.file_path not in result:
                result[item.file_path] = []
            result[item.file_path].append(item)
        return result
