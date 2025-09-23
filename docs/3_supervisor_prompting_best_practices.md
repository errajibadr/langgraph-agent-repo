## Research Supervisor Prompting Best Practices

## Research Agent Prompting Best Practices

### Prompt
First, we'll define a prompt that instructs our agent to use available search tools. To prevent excessive tool calls and maintain research focus, we use a few prompting techniques for agents:

#### 1. Think Like The Agent
What instructions would you give a new work colleague?

- Read the question carefully - What specific information does the user need?
- Start with broader searches - Use broad, comprehensive queries first.
- After each search, pause and assess - Do I have enough to answer? What's still missing?
- Execute narrower searches as you gather information - Fill in the gaps.

#### 2. Concrete Heuristics (Prevent "Spin-Out" on excessive tool calls)
Use Hard Limits to prevent the research agent from calling tools excessively:

- Stop when you can answer confidently - Don't keep searching for perfection.
- Give it budgets - Use 2-3 search tool calls for simple queries. Use up to 5 for complex queries.
- Limit - Always stop after 5 search tool calls if you cannot find the right source(s).

#### 3. Show Your Thinking
After each search tool calling, use `think_tool` to analyze the results:

- What key information did I find?
- What's missing?
- Do I have enough to answer the question comprehensively?
- Should I search more or provide my answer?

**Results**: These techniques transform problematic research behavior like:

"best coffee shops SF" → "Saint Frank Coffee details" → "Sightglass Coffee details" → "Ritual Coffee details" → etc. (20+ searches)

Into efficient patterns like:

"best coffee shops SF" → ThinkTool(analyze results) → "SF specialty coffee quality ratings" → ThinkTool(assess completeness) → provide answer (3-5 searches total)

The key insight: Think like a human researcher with limited time - this prevents the "spin-out problem" where agents continue searching indefinitely.

