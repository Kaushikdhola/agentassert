"""Terminal reporter using rich for beautiful output.

Produces output matching the design in Section 14 of the spec:

    $ agentassert run tests/

    AgentAssert v0.1.0 — Behavioral Testing Framework for AI Agents
    collecting ... 12 tests

    tests/test_research_agent.py
      ✓ test_calls_search_before_summary              (3 steps, $0.003, 1.2s)
      ✓ test_handles_search_failure_gracefully        (2 steps, $0.001, 0.8s)
      ✗ test_does_not_call_summarize_without_content  FAILED

    ══════════════════════════════════════════════════════
    FAILURES
    ══════════════════════════════════════════════════════
    ...
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from agentassert._version import __version__
from agentassert.core.outcome import OutcomeStatus

if TYPE_CHECKING:
    from agentassert.core.item import TestItem
    from agentassert.core.outcome import Outcome
    from agentassert.core.session import TestSession


class TerminalReporter:
    """
    Rich terminal reporter for AgentAssert test results.

    Displays colorful, pytest-like output during test execution.
    """

    def __init__(self, verbose: bool = False, quiet: bool = False) -> None:
        self._console = Console()
        self._verbose = verbose
        self._quiet = quiet
        self._current_file: Path | None = None
        self._failed_items: list[TestItem] = []

    def on_session_start(self, session: TestSession) -> None:
        if self._quiet:
            return

        self._console.print()
        self._console.print(
            f"[bold blue]AgentAssert v{__version__}[/bold blue] — "
            "[dim]Behavioral Testing Framework for AI Agents[/dim]"
        )
        self._console.print(f"[dim]collecting ...[/dim] {session.total_count} tests")
        self._console.print()

    def on_test_start(self, item: TestItem) -> None:
        if self._quiet:
            return

        # Print file header if we've moved to a new file
        if item.file_path != self._current_file:
            self._current_file = item.file_path
            self._console.print(f"[bold]{item.file_path}[/bold]")

    def on_test_finish(self, item: TestItem, outcome: Outcome) -> None:
        if outcome.status == OutcomeStatus.FAILED or outcome.status == OutcomeStatus.ERROR:
            self._failed_items.append(item)

        if self._quiet:
            # Just print dots
            if outcome.status == OutcomeStatus.PASSED:
                self._console.print(".", end="", style="green")
            elif outcome.status == OutcomeStatus.FAILED:
                self._console.print("F", end="", style="red bold")
            elif outcome.status == OutcomeStatus.ERROR:
                self._console.print("E", end="", style="red bold")
            elif outcome.status == OutcomeStatus.SKIPPED:
                self._console.print("s", end="", style="yellow")
            return

        # Build outcome line
        name = item.short_name
        status_icon = self._get_status_icon(outcome.status)
        metrics = self._format_metrics(outcome)

        if outcome.status == OutcomeStatus.PASSED:
            line = f"  {status_icon} {name}  [dim]{metrics}[/dim]"
        elif outcome.status == OutcomeStatus.FAILED:
            line = f"  {status_icon} {name}  [red bold]FAILED[/red bold]"
        elif outcome.status == OutcomeStatus.ERROR:
            line = f"  {status_icon} {name}  [red bold]ERROR[/red bold]"
        elif outcome.status == OutcomeStatus.SKIPPED:
            line = f"  {status_icon} {name}  [yellow]SKIPPED[/yellow]"
        else:
            line = f"  {status_icon} {name}"

        self._console.print(line)

    def on_session_finish(self, session: TestSession) -> None:
        if self._quiet:
            self._console.print()  # End the dots line

        # Print failures
        if self._failed_items:
            self._print_failures()

        # Print summary
        self._print_summary(session)

    def _get_status_icon(self, status: OutcomeStatus) -> str:
        icons = {
            OutcomeStatus.PASSED: "[green]✓[/green]",
            OutcomeStatus.FAILED: "[red]✗[/red]",
            OutcomeStatus.ERROR: "[red]![/red]",
            OutcomeStatus.SKIPPED: "[yellow]○[/yellow]",
        }
        return icons.get(status, "?")

    def _format_metrics(self, outcome: Outcome) -> str:
        parts = []
        if outcome.step_count > 0:
            parts.append(f"{outcome.step_count} steps")
        if outcome.total_cost_usd > 0:
            parts.append(f"${outcome.total_cost_usd:.4f}")
        if outcome.duration_seconds > 0:
            parts.append(f"{outcome.duration_seconds:.1f}s")
        return f"({', '.join(parts)})" if parts else ""

    def _print_failures(self) -> None:
        self._console.print()
        self._console.print("═" * 60, style="red")
        self._console.print("[bold red]FAILURES[/bold red]")
        self._console.print("═" * 60, style="red")

        for item in self._failed_items:
            if item.outcome is None:
                continue

            self._console.print()
            header = f"FAILED {item.file_path}::{item.short_name}"
            self._console.print(f"[bold red]{header}[/bold red]")

            if item.outcome.message:
                self._console.print(f"  [red]{item.outcome.message}[/red]")

            if self._verbose and item.outcome.traceback:
                self._console.print()
                self._console.print(
                    Panel(
                        item.outcome.traceback,
                        title="Traceback",
                        border_style="red",
                        expand=False,
                    )
                )

            self._console.print()
            self._console.print(
                f"  [dim]To replay: agentassert replay {item.node_id}[/dim]"
            )

    def _print_summary(self, session: TestSession) -> None:
        self._console.print()
        self._console.print("═" * 60)

        # Build summary parts
        parts = []
        if session.passed_count > 0:
            parts.append(f"[green]{session.passed_count} passed[/green]")
        if session.failed_count > 0:
            parts.append(f"[red]{session.failed_count} failed[/red]")
        if session.error_count > 0:
            parts.append(f"[red]{session.error_count} error[/red]")
        if session.skipped_count > 0:
            parts.append(f"[yellow]{session.skipped_count} skipped[/yellow]")

        summary = ", ".join(parts) if parts else "0 tests"
        duration = f"in {session.total_duration_seconds:.1f}s"

        self._console.print(f"{summary} {duration}")

        if session.total_cost_usd > 0:
            self._console.print(f"[dim]Total LLM cost: ${session.total_cost_usd:.4f}[/dim]")

        self._console.print("═" * 60)
        self._console.print()
