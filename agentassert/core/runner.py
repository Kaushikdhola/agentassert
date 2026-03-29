"""Test runner for executing AgentAssert tests.

The runner executes test items collected by the TestCollector,
manages fixtures, captures outcomes, and reports results.
"""

from __future__ import annotations

import inspect
import time
import traceback
from typing import Any, Callable

from agentassert.core.item import TestItem
from agentassert.core.outcome import Outcome
from agentassert.core.session import TestSession
from agentassert.fixtures import AgentHarness


class TestRunner:
    """
    Executes AgentAssert test items.

    The runner:
    - Sets up fixtures for each test
    - Executes the test function
    - Captures pass/fail/error outcomes
    - Records metrics (duration, steps, cost)

    Args:
        session: The TestSession containing items to run.
        seed: Random seed for deterministic execution.
        timeout_seconds: Per-test timeout (default 120).

    Example:
        >>> session = collector.collect()
        >>> runner = TestRunner(session)
        >>> runner.run_all()
        >>> print(f"Passed: {session.passed_count}/{session.total_count}")
    """

    def __init__(
        self,
        session: TestSession,
        seed: int = 42,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._session = session
        self._seed = seed
        self._timeout_seconds = timeout_seconds
        self._current_item: TestItem | None = None

    def run_all(self, reporter: Any | None = None) -> None:
        """
        Run all test items in the session.

        Args:
            reporter: Optional reporter to receive test events.
        """
        self._session.start_time = time.time()

        for item in self._session.items:
            self._run_item(item, reporter)

        self._session.end_time = time.time()

    def run_item(self, item: TestItem, reporter: Any | None = None) -> Outcome:
        """
        Run a single test item.

        Args:
            item: The TestItem to execute.
            reporter: Optional reporter.

        Returns:
            The test Outcome.
        """
        return self._run_item(item, reporter)

    def _run_item(self, item: TestItem, reporter: Any | None = None) -> Outcome:
        self._current_item = item
        start_time = time.time()

        if reporter and hasattr(reporter, "on_test_start"):
            reporter.on_test_start(item)

        try:
            # Build kwargs from fixtures
            kwargs = self._resolve_fixtures(item)

            # Execute the test function
            item.function(**kwargs)

            # Test passed
            duration = time.time() - start_time
            outcome = Outcome.passed(
                duration_seconds=duration,
                step_count=self._get_step_count(kwargs),
                total_tokens=self._get_tokens(kwargs),
                total_cost_usd=self._get_cost(kwargs),
            )

        except AssertionError as e:
            # Test failed (assertion)
            duration = time.time() - start_time
            outcome = Outcome.failed(
                message=str(e),
                exception=e,
                traceback=traceback.format_exc(),
                duration_seconds=duration,
                step_count=self._get_step_count(kwargs) if "kwargs" in dir() else 0,
                total_tokens=self._get_tokens(kwargs) if "kwargs" in dir() else 0,
                total_cost_usd=self._get_cost(kwargs) if "kwargs" in dir() else 0.0,
            )

        except Exception as e:
            # Test errored (unhandled exception)
            duration = time.time() - start_time
            outcome = Outcome.error(
                message=str(e),
                exception=e,
                traceback=traceback.format_exc(),
                duration_seconds=duration,
            )

        item.set_outcome(outcome)

        if reporter and hasattr(reporter, "on_test_finish"):
            reporter.on_test_finish(item, outcome)

        self._current_item = None
        return outcome

    def _resolve_fixtures(self, item: TestItem) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        sig = inspect.signature(item.function)

        for param_name in sig.parameters:
            if param_name == "agent_harness":
                # Built-in harness fixture
                kwargs["agent_harness"] = AgentHarness(test_id=item.node_id)

            elif param_name == "scenario":
                # Scenario fixture for parametrized tests
                scenarios = getattr(item.function, "__agentassert_scenarios__", None)
                if scenarios and item.scenario_index is not None:
                    kwargs["scenario"] = scenarios[item.scenario_index]

            else:
                # Look up in session fixtures
                fixture_factory = self._session.get_fixture(param_name)
                if fixture_factory is not None:
                    kwargs[param_name] = fixture_factory()

        return kwargs

    def _get_step_count(self, kwargs: dict[str, Any]) -> int:
        harness = kwargs.get("agent_harness")
        if harness and hasattr(harness, "_last_trace"):
            trace = harness._last_trace
            if trace:
                return trace.step_count
        return 0

    def _get_tokens(self, kwargs: dict[str, Any]) -> int:
        harness = kwargs.get("agent_harness")
        if harness and hasattr(harness, "_last_trace"):
            trace = harness._last_trace
            if trace:
                return trace.total_tokens
        return 0

    def _get_cost(self, kwargs: dict[str, Any]) -> float:
        harness = kwargs.get("agent_harness")
        if harness and hasattr(harness, "_last_trace"):
            trace = harness._last_trace
            if trace:
                return trace.total_cost_usd
        return 0.0
