<p align="center">
  <img src="https://img.shields.io/badge/AgentUnit-v0.1.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange?style=for-the-badge" alt="License">
</p>

<h1 align="center">AgentUnit</h1>

<p align="center">
  <strong>The Behavioral Testing Framework for AI Agents</strong>
</p>

<p align="center">
  <em>"pytest for AI Agents" — Write tests. Run agents. Ship with confidence.</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## The Problem

Teams building AI agents face a critical gap in their development workflow:

| What Exists | What's Missing |
|-------------|----------------|
| Observability (LangSmith, Langfuse) | Behavioral test runners |
| Evaluation dashboards | CI/CD pass/fail gates |
| LLM output quality metrics | Agent execution path testing |

**AgentUnit fills this gap.** It's an open-source, framework-agnostic, local-first behavioral test framework designed specifically for AI agent pipelines.

## Why AgentUnit?

- **Framework Agnostic** — Works with LangChain, CrewAI, AutoGen, LlamaIndex, or raw API calls
- **Local First** — No cloud accounts, no dashboards, no external services required
- **CI/CD Native** — Designed for `git push → test → deploy` workflows
- **Deterministic** — Seeded execution for reproducible test runs
- **Developer Friendly** — Familiar pytest-like syntax and workflow

---

## Quick Start

### Installation

```bash
pip install agentunit
```

### Write Your First Test

```python
# tests/test_my_agent.py
from agentunit import agent_test, expect, mock_tool, contains

@agent_test
def test_research_agent_workflow(agent_harness):
    """Test that the research agent follows the correct tool sequence."""
    
    # 1. Create mock tools with deterministic responses
    search = mock_tool("web_search", returns={"results": ["AI breakthrough news"]})
    summarize = mock_tool("summarize", returns="Key finding: AI is advancing rapidly")

    # 2. Run your agent under test
    trace = agent_harness.run(
        agent=my_research_agent,
        input="Find the latest AI news",
        tools=[search, summarize]
    )

    # 3. Assert on behavioral expectations
    expect(trace).tool("web_search").was_called()
    expect(trace).tool("web_search").called_before("summarize")
    expect(trace).tool("web_search").called_with(query=contains("AI"))
    expect(trace).completed_within_steps(10)
    expect(trace).output.not_empty()
```

### Run Your Tests

```bash
$ agentunit run tests/

AgentUnit v0.1.0 — Behavioral Testing Framework for AI Agents
collecting ... 3 tests

tests/test_my_agent.py
  ✓ test_research_agent_workflow        (2 steps, $0.002, 0.3s)
  ✓ test_handles_api_failure            (1 steps, $0.001, 0.1s)
  ✓ test_stays_within_budget            (4 steps, $0.008, 0.5s)

════════════════════════════════════════════════════════════
3 passed in 0.9s
════════════════════════════════════════════════════════════
```

---

## Features

### Mock Tools

Create deterministic tool responses for predictable testing:

```python
# Static response
search = mock_tool("web_search", returns={"results": ["item1", "item2"]})

# Sequential responses
api = mock_tool("api_call", returns_sequence=[
    {"status": "pending"},
    {"status": "processing"},
    {"status": "complete"}
])

# Simulate failures
flaky_api = mock_tool("external_service", raises=ConnectionError("timeout"))

# Rate limiting simulation
limited_api = mock_tool("rate_limited_api", returns="ok", fail_after=5)
```

### Behavioral Assertions

Assert on how your agent behaves, not just what it outputs:

```python
# Tool invocation assertions
expect(trace).tool("search").was_called()
expect(trace).tool("search").was_not_called()
expect(trace).tool("search").called_exactly(3)
expect(trace).tool("search").called_at_least(1)

# Execution order assertions
expect(trace).tool("fetch_data").called_before("process_data")
expect(trace).tool("cleanup").called_after("main_task")

# Argument matching with flexible matchers
expect(trace).tool("api").called_with(
    query=contains("search term"),
    limit=greater_than(0),
    filters=has_key("category")
)

# Execution behavior assertions
expect(trace).completed()
expect(trace).completed_within_steps(15)
expect(trace).failed_gracefully()

# Output assertions
expect(trace).output.not_empty()
expect(trace).output.contains("success")
expect(trace).output.is_valid_json()
```

### Rich Matchers

Flexible matchers for complex assertion scenarios:

```python
from agentunit import (
    # String matchers
    contains, matches, starts_with, ends_with, any_string,
    
    # Numeric matchers
    greater_than, less_than, between,
    
    # Collection matchers
    has_key, has_length, contains_item,
    
    # Logical matchers
    all_of, any_of, not_, anything
)

# Combine matchers for precise assertions
expect(trace).tool("search").called_with(
    query=all_of(
        starts_with("user:"),
        contains("search"),
        not_(contains("admin"))
    )
)
```

---

## CLI Reference

```bash
# Run all tests in current directory
agentunit run

# Run tests in a specific directory
agentunit run tests/

# Run a specific test file
agentunit run tests/test_research_agent.py

# Filter tests by keyword
agentunit run -k "search"

# Verbose output with full tracebacks
agentunit run -v

# Minimal output (dots only)
agentunit run -q

# Set random seed for reproducibility
agentunit run --seed 12345

# Stop on first failure
agentunit run -x
```

---

## Framework Integration

AgentUnit is designed to work with any agent framework:

<table>
<tr>
<td width="50%">

**LangChain**
```python
@agent_test
def test_langchain_agent(agent_harness):
    from langchain.agents import AgentExecutor
    
    trace = agent_harness.run(
        agent=my_langchain_agent,
        input="Analyze this data"
    )
    expect(trace).completed()
```

</td>
<td width="50%">

**Custom Agents**
```python
@agent_test
def test_custom_agent(agent_harness):
    def my_agent(prompt, tools):
        # Your custom logic
        return result
    
    trace = agent_harness.run(
        agent=my_agent,
        input="Process request"
    )
    expect(trace).completed()
```

</td>
</tr>
</table>

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install agentunit
          pip install -r requirements.txt
      
      - name: Run agent tests
        run: agentunit run tests/ -v
```

### GitLab CI

```yaml
agent-tests:
  image: python:3.11
  script:
    - pip install agentunit
    - agentunit run tests/
```

---

## Comparison with Alternatives

| Feature | AgentUnit | LangSmith | Langfuse | DeepEval |
|---------|-----------|-----------|----------|----------|
| Local execution | Yes | No | Partial | Yes |
| No account required | Yes | No | No | Yes |
| Framework agnostic | Yes | No | Yes | Yes |
| Behavioral assertions | Yes | No | No | No |
| Tool call testing | Yes | Partial | Partial | No |
| CI/CD native | Yes | Partial | Partial | Yes |
| Deterministic replay | Yes | No | No | No |

---

## Documentation

- **[Sample Tests](tests/test_sample.py)** — Working examples to get started
- **[Contributing Guide](CONTRIBUTING.md)** — How to contribute to the project

---

## Contributing

We welcome contributions from the community. Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

---

## License

AgentUnit is released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built by <a href="https://github.com/kaushikdhola">Kaushik Dhola</a></strong>
</p>

<p align="center">
  <code>pip install agentunit</code>
</p>