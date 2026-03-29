"""Decorators for AgentAssert test and fixture definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class Scenario:
    """Represents a named scenario payload for parametrized agent tests."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, item: str) -> Any:
        """Expose scenario params as attributes for fluent access in tests."""
        if item in self.params:
            return self.params[item]
        raise AttributeError(f"Scenario {self.name!r} has no attribute {item!r}.")


def scenario(name: str, **kwargs: Any) -> Scenario:
    """Create a scenario object used by `@scenarios([...])`."""
    return Scenario(name=name, params=kwargs)


def scenarios(values: list[Scenario]) -> Callable[[F], F]:
    """Attach scenario definitions to a test function."""

    def decorator(func: F) -> F:
        setattr(func, "__agentassert_scenarios__", values)
        return func

    return decorator


def agent_test(func: F) -> F:
    """
    Mark a function as an AgentAssert test.

    The collector discovers tests by looking for this marker.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    setattr(wrapper, "__agentassert_test__", True)
    return wrapper  # type: ignore[return-value]


def fixture(func: F) -> F:
    """
    Mark a function as an AgentAssert fixture.

    Fixtures are discovered from `conftest.py` files and can be injected
    into agent tests.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    setattr(wrapper, "__agentassert_fixture__", True)
    return wrapper  # type: ignore[return-value]
