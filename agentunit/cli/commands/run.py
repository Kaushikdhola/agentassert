"""Run command for AgentUnit CLI.

Usage:
    agentunit run [PATH] [OPTIONS]

Examples:
    agentunit run                    # Run all tests in current directory
    agentunit run tests/             # Run tests in tests/ directory
    agentunit run tests/test_foo.py  # Run tests in specific file
    agentunit run -k "search"        # Run tests matching "search"
    agentunit run -v                 # Verbose output
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
    default=".",
)
@click.option(
    "-k",
    "--keyword",
    "keyword",
    type=str,
    default=None,
    help="Only run tests matching the given keyword expression.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Increase verbosity. Show tracebacks on failures.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    default=False,
    help="Decrease verbosity. Output dots only.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for deterministic test ordering.",
)
@click.option(
    "-x",
    "--exitfirst",
    is_flag=True,
    default=False,
    help="Exit immediately on first failure.",
)
@click.option(
    "--tb",
    "traceback_style",
    type=click.Choice(["short", "long", "no"]),
    default="short",
    help="Traceback style: short, long, or no.",
)
def run(
    path: Path,
    keyword: Optional[str],
    verbose: bool,
    quiet: bool,
    seed: Optional[int],
    exitfirst: bool,
    traceback_style: str,
) -> None:
    """
    Run AgentUnit tests.

    Discovers and executes @agent_test decorated tests from the given path.
    PATH can be a directory or a specific test file. Defaults to current directory.
    """
    from agentunit.core.collector import TestCollector
    from agentunit.core.runner import TestRunner
    from agentunit.reporters.terminal import TerminalReporter

    # Create reporter
    reporter = TerminalReporter(verbose=verbose, quiet=quiet)

    # Collect tests
    collector = TestCollector(paths=[path])
    session = collector.collect()
    session.seed = seed

    items = list(session.items)

    # Filter by keyword if given
    if keyword:
        filtered_items = [item for item in items if keyword.lower() in item.node_id.lower()]
        # Create new session with only filtered items
        from agentunit.core.session import TestSession
        session = TestSession(seed=seed)
        for item in filtered_items:
            session.add_item(item)

    # Report session start
    reporter.on_session_start(session)

    # Create runner
    runner = TestRunner(
        session=session,
        seed=seed or 42,
    )

    # Run tests
    runner.run_all(reporter=reporter)

    # Report session finish
    reporter.on_session_finish(session)

    # Exit with appropriate code
    exit_code = 0 if session.failed_count == 0 and session.error_count == 0 else 1
    raise SystemExit(exit_code)
