"""Test outcome representation for AgentAssert."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OutcomeStatus(str, Enum):
    """Status of a test execution."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class Outcome(BaseModel):
    """
    Represents the outcome of a single test execution.

    Attributes:
        status: The final status of the test (passed, failed, error, skipped).
        message: Optional message describing the outcome (e.g., failure reason).
        exception: The exception that caused a failure or error, if any.
        exception_type: The type name of the exception, if any.
        traceback: The formatted traceback string, if an exception occurred.
        duration_seconds: How long the test took to execute.
        step_count: Number of steps (LLM + tool calls) in the agent execution.
        total_tokens: Total tokens consumed during the test.
        total_cost_usd: Total cost in USD for the test execution.
    """

    status: OutcomeStatus
    message: str | None = None
    exception: Any | None = Field(default=None, exclude=True)
    exception_type: str | None = None
    traceback: str | None = None
    duration_seconds: float = 0.0
    step_count: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def passed(
        cls,
        duration_seconds: float = 0.0,
        step_count: int = 0,
        total_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> "Outcome":
        """Create a passed outcome."""
        return cls(
            status=OutcomeStatus.PASSED,
            duration_seconds=duration_seconds,
            step_count=step_count,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
        )

    @classmethod
    def failed(
        cls,
        message: str,
        exception: BaseException | None = None,
        traceback: str | None = None,
        duration_seconds: float = 0.0,
        step_count: int = 0,
        total_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> "Outcome":
        """Create a failed outcome (assertion failure)."""
        return cls(
            status=OutcomeStatus.FAILED,
            message=message,
            exception=exception,
            exception_type=type(exception).__name__ if exception else None,
            traceback=traceback,
            duration_seconds=duration_seconds,
            step_count=step_count,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
        )

    @classmethod
    def error(
        cls,
        message: str,
        exception: BaseException | None = None,
        traceback: str | None = None,
        duration_seconds: float = 0.0,
    ) -> "Outcome":
        """Create an error outcome (unhandled exception)."""
        return cls(
            status=OutcomeStatus.ERROR,
            message=message,
            exception=exception,
            exception_type=type(exception).__name__ if exception else None,
            traceback=traceback,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def skipped(cls, message: str | None = None) -> "Outcome":
        """Create a skipped outcome."""
        return cls(
            status=OutcomeStatus.SKIPPED,
            message=message,
        )

    @property
    def is_success(self) -> bool:
        """Return True if the test passed or was skipped."""
        return self.status in (OutcomeStatus.PASSED, OutcomeStatus.SKIPPED)

    @property
    def is_failure(self) -> bool:
        """Return True if the test failed or errored."""
        return self.status in (OutcomeStatus.FAILED, OutcomeStatus.ERROR)
