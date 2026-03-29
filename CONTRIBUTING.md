# Contributing to AgentUnit

Thank you for your interest in contributing to AgentUnit.

This document outlines the guidelines for contributing to the project. Please read through before submitting your first contribution.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Attribution](#attribution)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

---

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

When reporting bugs, include:

1. **Clear title** describing the issue
2. **Steps to reproduce** the behavior
3. **Expected behavior** — what you expected to happen
4. **Actual behavior** — what actually happened
5. **Environment details** — Python version, OS, AgentUnit version
6. **Code samples** — minimal reproducible example if possible

### Suggesting Features

We love feature suggestions! Please include:

1. **Clear description** of the feature
2. **Use case** — why is this feature needed?
3. **Proposed implementation** (optional)
4. **Alternatives considered** (optional)

### Improving Documentation

Documentation improvements are always welcome:

- Fix typos or unclear wording
- Add examples and tutorials
- Improve API documentation
- Translate documentation

### Submitting Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests
5. Run the test suite
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- Git

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/agentunit.git
cd agentunit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests to verify setup
agentunit run tests/
```

### Running Tests

```bash
# Run all tests
agentunit run tests/

# Run with verbose output
agentunit run tests/ -v

# Run specific test file
agentunit run tests/test_sample.py
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy agentunit/
```

---

## Pull Request Process

1. **Update documentation** if you're changing functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass** before submitting
4. **Follow the style guidelines** below
5. **Write clear commit messages**
6. **Link related issues** in your PR description

### PR Title Format

Use clear, descriptive titles:

- `feat: Add support for async agents`
- `fix: Handle empty tool responses correctly`
- `docs: Improve getting started guide`
- `test: Add tests for matcher edge cases`

---

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all public functions
- Maximum line length: 100 characters
- Use docstrings for all public modules, classes, and functions

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param2 is negative.
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")
    return len(param1) > param2
```

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep the first line under 72 characters
- Reference issues and PRs in the body when relevant

---

## Attribution

### Contributor Recognition

All contributors will be recognized in:

- The project's contributors list
- Release notes for significant contributions
- Special acknowledgments for major features

### License Agreement

By contributing to AgentUnit, you agree that your contributions will be licensed under the MIT License. You also confirm that you have the right to submit the contribution.

---

## Questions?

If you have questions about contributing, feel free to open a Discussion on GitHub or reach out to the maintainers.

---

*Thank you for helping improve AgentUnit.*
