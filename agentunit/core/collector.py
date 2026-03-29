"""Test collector for discovering AgentUnit tests.

The collector scans directories for test files (test_*.py, *_test.py) and
discovers functions decorated with @agent_test.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

from agentunit.core.item import TestItem
from agentunit.core.session import TestSession


class TestCollector:
    """
    Discovers and collects AgentUnit test items.

    The collector mimics pytest's discovery pattern:
    - Scans directories for test_*.py and *_test.py files
    - Discovers conftest.py files for fixtures
    - Finds functions marked with @agent_test decorator
    - Builds TestItem objects for each discovered test

    Args:
        paths: List of paths (files or directories) to scan.
        python_files: Glob patterns for test files.
        python_functions: Prefixes for test function names.

    Example:
        >>> collector = TestCollector(paths=[Path("tests/")])
        >>> session = collector.collect()
        >>> print(f"Found {session.total_count} tests")
    """

    DEFAULT_FILE_PATTERNS = ["test_*.py", "*_test.py"]
    DEFAULT_FUNCTION_PREFIXES = ["test_"]

    def __init__(
        self,
        paths: list[Path] | None = None,
        python_files: list[str] | None = None,
        python_functions: list[str] | None = None,
    ) -> None:
        self._paths = paths or [Path("tests/")]
        self._file_patterns = python_files or self.DEFAULT_FILE_PATTERNS
        self._function_prefixes = python_functions or self.DEFAULT_FUNCTION_PREFIXES
        self._session = TestSession()
        self._conftest_fixtures: dict[str, Callable[..., Any]] = {}

    def collect(self) -> TestSession:
        """
        Run the collection process and return a TestSession.

        Returns:
            TestSession containing all discovered test items and fixtures.
        """
        # First pass: discover conftest.py files and load fixtures
        for path in self._paths:
            self._discover_conftest(path)

        # Second pass: discover test files and functions
        for path in self._paths:
            self._collect_from_path(path)

        # Add fixtures to session
        for name, factory in self._conftest_fixtures.items():
            self._session.add_fixture(name, factory)

        return self._session

    def _discover_conftest(self, path: Path) -> None:
        """Discover and load fixtures from conftest.py files."""
        if path.is_file():
            conftest_path = path.parent / "conftest.py"
        else:
            conftest_path = path / "conftest.py"

        if conftest_path.exists():
            self._load_conftest(conftest_path)

        # Also check parent directories up to the root
        if path.is_dir():
            for parent in path.parents:
                parent_conftest = parent / "conftest.py"
                if parent_conftest.exists():
                    self._load_conftest(parent_conftest)

    def _load_conftest(self, conftest_path: Path) -> None:
        """Load fixtures from a conftest.py file."""
        module = self._import_module_from_path(conftest_path)
        if module is None:
            return

        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, "__agentunit_fixture__"):
                self._conftest_fixtures[name] = obj

    def _collect_from_path(self, path: Path) -> None:
        """Collect tests from a file or directory."""
        if not path.exists():
            return

        if path.is_file():
            if self._is_test_file(path):
                self._collect_from_file(path)
        else:
            # Recursively scan directory
            for pattern in self._file_patterns:
                for test_file in path.rglob(pattern):
                    self._collect_from_file(test_file)

    def _is_test_file(self, path: Path) -> bool:
        """Check if a file matches test file patterns."""
        name = path.name
        for pattern in self._file_patterns:
            # Simple pattern matching (test_*.py, *_test.py)
            if pattern.startswith("*"):
                suffix = pattern[1:]
                if name.endswith(suffix):
                    return True
            elif pattern.endswith("*"):
                prefix = pattern[:-1]
                if name.startswith(prefix):
                    return True
            elif "*" in pattern:
                prefix, suffix = pattern.split("*", 1)
                if name.startswith(prefix) and name.endswith(suffix):
                    return True
        return False

    def _collect_from_file(self, file_path: Path) -> None:
        """Collect test items from a single Python file."""
        # First, use AST to find test function names and line numbers
        test_functions = self._find_test_functions_ast(file_path)
        if not test_functions:
            return

        # Import the module to get the actual function objects
        module = self._import_module_from_path(file_path)
        if module is None:
            return

        module_name = self._path_to_module_name(file_path)

        for func_name, line_number in test_functions:
            func = getattr(module, func_name, None)
            if func is None:
                continue

            # Check for @agent_test decorator
            if not hasattr(func, "__agentunit_test__"):
                continue

            # Check for scenarios
            scenarios = getattr(func, "__agentunit_scenarios__", None)
            if scenarios:
                # Create a TestItem for each scenario
                for idx, scenario in enumerate(scenarios):
                    item = TestItem(
                        name=func_name,
                        function=func,
                        file_path=file_path,
                        line_number=line_number,
                        module_name=module_name,
                        scenario_index=idx,
                        scenario_name=scenario.name if hasattr(scenario, "name") else None,
                    )
                    self._session.add_item(item)
            else:
                # Single test item
                item = TestItem(
                    name=func_name,
                    function=func,
                    file_path=file_path,
                    line_number=line_number,
                    module_name=module_name,
                )
                self._session.add_item(item)

    def _find_test_functions_ast(self, file_path: Path) -> list[tuple[str, int]]:
        """
        Parse a file with AST to find test function names and line numbers.

        Returns:
            List of (function_name, line_number) tuples.
        """
        try:
            source = file_path.read_text()
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return []

        functions: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function name starts with test prefix
                for prefix in self._function_prefixes:
                    if node.name.startswith(prefix):
                        functions.append((node.name, node.lineno))
                        break

        return functions

    def _import_module_from_path(self, file_path: Path) -> Any | None:
        """Dynamically import a module from a file path."""
        module_name = self._path_to_module_name(file_path)

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None

    def _path_to_module_name(self, file_path: Path) -> str:
        """Convert a file path to a Python module name."""
        # Remove .py extension and convert path separators to dots
        parts = file_path.with_suffix("").parts

        # Try to find the root (where we started scanning)
        for base_path in self._paths:
            if base_path.is_file():
                base_path = base_path.parent
            try:
                rel_path = file_path.with_suffix("").relative_to(base_path.parent)
                return ".".join(rel_path.parts)
            except ValueError:
                continue

        # Fallback: use the last few parts
        return ".".join(parts[-3:]) if len(parts) >= 3 else ".".join(parts)
