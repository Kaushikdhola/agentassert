"""Matchers for use in AgentAssert assertions.

Matchers are used with `called_with()` and similar assertions to perform
flexible value matching beyond simple equality.

Example:
    >>> expect(trace).tool("search").called_with(query=au.contains("AI"))
    >>> expect(trace).tool("api").called_with(count=au.between(1, 10))
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class Matcher(ABC):
    """
    Base class for all matchers.

    Matchers implement a `matches(value)` method that returns True
    if the value satisfies the matcher's condition.
    """

    @abstractmethod
    def matches(self, value: Any) -> bool:
        """Return True if value matches the condition."""

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of the matcher."""

    def __repr__(self) -> str:
        return f"<{self.describe()}>"


# String Matchers

class ContainsMatcher(Matcher):

    def __init__(self, substring: str) -> None:
        self._substring = substring

    def matches(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return self._substring in value

    def describe(self) -> str:
        return f"contains({self._substring!r})"


class MatchesMatcher(Matcher):
    """Matches if the value matches a regex pattern."""

    def __init__(self, pattern: str) -> None:
        self._pattern = pattern
        self._regex = re.compile(pattern)

    def matches(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self._regex.search(value))

    def describe(self) -> str:
        return f"matches({self._pattern!r})"


class StartsWithMatcher(Matcher):
    """Matches if the value starts with a prefix."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def matches(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return value.startswith(self._prefix)

    def describe(self) -> str:
        return f"starts_with({self._prefix!r})"


class EndsWithMatcher(Matcher):
    """Matches if the value ends with a suffix."""

    def __init__(self, suffix: str) -> None:
        self._suffix = suffix

    def matches(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return value.endswith(self._suffix)

    def describe(self) -> str:
        return f"ends_with({self._suffix!r})"


class AnyStringMatcher(Matcher):
    """Matches any string value."""

    def matches(self, value: Any) -> bool:
        return isinstance(value, str)

    def describe(self) -> str:
        return "any_string()"


# Numeric Matchers

class GreaterThanMatcher(Matcher):

    def __init__(self, threshold: float | int) -> None:
        self._threshold = threshold

    def matches(self, value: Any) -> bool:
        try:
            return value > self._threshold
        except TypeError:
            return False

    def describe(self) -> str:
        return f"greater_than({self._threshold})"


class LessThanMatcher(Matcher):
    """Matches if value is less than a threshold."""

    def __init__(self, threshold: float | int) -> None:
        self._threshold = threshold

    def matches(self, value: Any) -> bool:
        try:
            return value < self._threshold
        except TypeError:
            return False

    def describe(self) -> str:
        return f"less_than({self._threshold})"


class BetweenMatcher(Matcher):
    """Matches if value is between two bounds (inclusive)."""

    def __init__(self, low: float | int, high: float | int) -> None:
        self._low = low
        self._high = high

    def matches(self, value: Any) -> bool:
        try:
            return self._low <= value <= self._high
        except TypeError:
            return False

    def describe(self) -> str:
        return f"between({self._low}, {self._high})"


# Collection Matchers

class HasKeyMatcher(Matcher):

    def __init__(self, key: str) -> None:
        self._key = key

    def matches(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        return self._key in value

    def describe(self) -> str:
        return f"has_key({self._key!r})"


class HasLengthMatcher(Matcher):
    """Matches if the value has a specific length."""

    def __init__(self, length: int) -> None:
        self._length = length

    def matches(self, value: Any) -> bool:
        try:
            return len(value) == self._length
        except TypeError:
            return False

    def describe(self) -> str:
        return f"has_length({self._length})"


class ContainsItemMatcher(Matcher):
    """Matches if a collection contains a specific item."""

    def __init__(self, item: Any) -> None:
        self._item = item

    def matches(self, value: Any) -> bool:
        try:
            return self._item in value
        except TypeError:
            return False

    def describe(self) -> str:
        return f"contains_item({self._item!r})"


# Type Matchers

class IsTypeMatcher(Matcher):

    def __init__(self, expected_type: type) -> None:
        self._type = expected_type

    def matches(self, value: Any) -> bool:
        return isinstance(value, self._type)

    def describe(self) -> str:
        return f"is_type({self._type.__name__})"


class IsNotNoneMatcher(Matcher):
    """Matches any non-None value."""

    def matches(self, value: Any) -> bool:
        return value is not None

    def describe(self) -> str:
        return "is_not_none()"


class IsNoneMatcher(Matcher):
    """Matches only None."""

    def matches(self, value: Any) -> bool:
        return value is None

    def describe(self) -> str:
        return "is_none()"


class AnythingMatcher(Matcher):
    """Matches any value (always returns True)."""

    def matches(self, value: Any) -> bool:
        return True

    def describe(self) -> str:
        return "anything()"


# Composite Matchers

class AllOfMatcher(Matcher):

    def __init__(self, *matchers: Matcher) -> None:
        self._matchers = matchers

    def matches(self, value: Any) -> bool:
        return all(m.matches(value) for m in self._matchers)

    def describe(self) -> str:
        inner = ", ".join(m.describe() for m in self._matchers)
        return f"all_of({inner})"


class AnyOfMatcher(Matcher):
    """Matches if any child matcher matches."""

    def __init__(self, *matchers: Matcher) -> None:
        self._matchers = matchers

    def matches(self, value: Any) -> bool:
        return any(m.matches(value) for m in self._matchers)

    def describe(self) -> str:
        inner = ", ".join(m.describe() for m in self._matchers)
        return f"any_of({inner})"


class NotMatcher(Matcher):
    """Matches if the child matcher does not match."""

    def __init__(self, matcher: Matcher) -> None:
        self._matcher = matcher

    def matches(self, value: Any) -> bool:
        return not self._matcher.matches(value)

    def describe(self) -> str:
        return f"not_({self._matcher.describe()})"


# Factory functions (public API)

def contains(substring: str) -> ContainsMatcher:
    return ContainsMatcher(substring)


def matches(pattern: str) -> MatchesMatcher:
    return MatchesMatcher(pattern)


def starts_with(prefix: str) -> StartsWithMatcher:
    return StartsWithMatcher(prefix)


def ends_with(suffix: str) -> EndsWithMatcher:
    return EndsWithMatcher(suffix)


def any_string() -> AnyStringMatcher:
    return AnyStringMatcher()


def greater_than(threshold: float | int) -> GreaterThanMatcher:
    return GreaterThanMatcher(threshold)


def less_than(threshold: float | int) -> LessThanMatcher:
    return LessThanMatcher(threshold)


def between(low: float | int, high: float | int) -> BetweenMatcher:
    return BetweenMatcher(low, high)


def has_key(key: str) -> HasKeyMatcher:
    return HasKeyMatcher(key)


def has_length(length: int) -> HasLengthMatcher:
    return HasLengthMatcher(length)


def contains_item(item: Any) -> ContainsItemMatcher:
    return ContainsItemMatcher(item)


def is_type(expected_type: type) -> IsTypeMatcher:
    return IsTypeMatcher(expected_type)


def is_not_none() -> IsNotNoneMatcher:
    return IsNotNoneMatcher()


def is_none() -> IsNoneMatcher:
    return IsNoneMatcher()


def anything() -> AnythingMatcher:
    return AnythingMatcher()


def all_of(*matchers: Matcher) -> AllOfMatcher:
    return AllOfMatcher(*matchers)


def any_of(*matchers: Matcher) -> AnyOfMatcher:
    return AnyOfMatcher(*matchers)


def not_(matcher: Matcher) -> NotMatcher:
    return NotMatcher(matcher)
