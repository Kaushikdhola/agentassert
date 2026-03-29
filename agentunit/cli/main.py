"""AgentUnit CLI main entry point.

Usage:
    agentunit run [PATH] [OPTIONS]
    agentunit replay TRACE_ID
    agentunit --help

Per Section 14 of the spec.
"""

from __future__ import annotations

import click

from agentunit._version import __version__


@click.group()
@click.version_option(version=__version__, prog_name="agentunit")
def main() -> None:
    """
    AgentUnit — Behavioral Testing Framework for AI Agents

    Run behavioral tests for AI agent pipelines with deterministic
    replay, cost tracking, and behavioral assertions.
    """
    pass


# Import and register commands
from agentunit.cli.commands.run import run as run_cmd

main.add_command(run_cmd)


if __name__ == "__main__":
    main()
