"""Sample tests demonstrating AgentUnit capabilities.

These tests show the full end-to-end workflow:
1. Create mock tools with predefined responses
2. Run an agent that uses those tools
3. Assert on the agent's behavior using the captured trace
"""

from agentassert import agent_test, expect, mock_tool, contains


# ═══════════════════════════════════════════════════════════════════════════════
# Sample agents for testing
# ═══════════════════════════════════════════════════════════════════════════════

def simple_research_agent(prompt: str, tools: list = None):
    """
    Mock agent that simulates a research workflow:
    1. Calls web_search to find information
    2. Calls summarize to summarize the results
    """
    tools = tools or []
    results = []
    
    # Find and call search tool
    for tool in tools:
        if tool.name == "web_search":
            result = tool(query=prompt)
            results.append(result)
            break
    
    # Find and call summarize tool
    for tool in tools:
        if tool.name == "summarize":
            summary = tool(text=str(results))
            return {"summary": summary, "sources": results}
    
    return {"summary": "No summary available", "sources": results}


def calculator_agent(prompt: str, tools: list = None):
    """Mock agent that uses a calculator tool."""
    tools = tools or []
    for tool in tools:
        if tool.name == "calculator":
            result = tool(expression=prompt)
            return f"The answer is: {result}"
    return "No calculator available"


# ═══════════════════════════════════════════════════════════════════════════════
# Behavioral Tests
# ═══════════════════════════════════════════════════════════════════════════════

@agent_test
def test_search_called_before_summarize(agent_harness):
    """Test that the agent calls search before summarize."""
    search = mock_tool("web_search", returns={"results": ["AI news item 1"]})
    summarize = mock_tool("summarize", returns="AI is advancing rapidly")

    trace = agent_harness.run(
        agent=simple_research_agent,
        input="Find AI news",
        tools=[search, summarize],
    )

    # Assert both tools were called
    expect(trace).tool("web_search").was_called()
    expect(trace).tool("summarize").was_called()
    
    # Assert correct ordering
    expect(trace).tool("web_search").called_before("summarize")


@agent_test
def test_search_called_with_correct_query(agent_harness):
    """Test that search is called with the user's query."""
    search = mock_tool("web_search", returns={"results": ["result"]})
    summarize = mock_tool("summarize", returns="Summary")

    trace = agent_harness.run(
        agent=simple_research_agent,
        input="Find AI news",
        tools=[search, summarize],
    )

    # Assert search was called with a query containing "AI"
    expect(trace).tool("web_search").called_with(query=contains("AI"))


@agent_test
def test_tool_called_exactly_once(agent_harness):
    """Test that a tool is called exactly once."""
    calc = mock_tool("calculator", returns=42)

    trace = agent_harness.run(
        agent=calculator_agent,
        input="2 + 2",
        tools=[calc],
    )

    expect(trace).tool("calculator").called_exactly(1)


@agent_test  
def test_completes_within_step_limit(agent_harness):
    """Test that agent completes within step limit."""
    search = mock_tool("web_search", returns={"results": []})

    trace = agent_harness.run(
        agent=simple_research_agent,
        input="Quick search",
        tools=[search],
    )

    # 1 tool call should be well under 10 steps
    expect(trace).completed_within_steps(10)


@agent_test
def test_output_contains_expected_content(agent_harness):
    """Test that agent output contains expected content."""
    search = mock_tool("web_search", returns={"results": ["Important finding"]})
    summarize = mock_tool("summarize", returns="Key insight from research")

    trace = agent_harness.run(
        agent=simple_research_agent,
        input="Research topic",
        tools=[search, summarize],
    )

    expect(trace).output.not_empty()
    expect(trace).completed()


@agent_test
def test_tool_not_called_when_not_needed(agent_harness):
    """Test that unnecessary tools are not called."""
    search = mock_tool("web_search", returns={"results": []})
    unused_tool = mock_tool("unused_api", returns="should not be called")

    trace = agent_harness.run(
        agent=simple_research_agent,
        input="Search query",
        tools=[search, unused_tool],
    )

    expect(trace).tool("web_search").was_called()
    expect(trace).tool("unused_api").was_not_called()


@agent_test
def test_mock_tool_sequence(agent_harness):
    """Test that mock tools can return different values in sequence."""
    # Tool returns different values on each call
    search = mock_tool(
        "web_search",
        returns_sequence=[
            {"results": ["First result"]},
            {"results": ["Second result"]},
        ]
    )

    def multi_search_agent(prompt: str, tools: list = None):
        """Agent that searches twice."""
        tools = tools or []
        results = []
        for tool in tools:
            if tool.name == "web_search":
                results.append(tool(query="first"))
                results.append(tool(query="second"))
        return results

    trace = agent_harness.run(
        agent=multi_search_agent,
        input="Multi-search",
        tools=[search],
    )

    expect(trace).tool("web_search").called_exactly(2)
