## Context Engineering

### Overview
Our research agent performs iterative tool-calling to search for information. The agent follows a simple yet effective pattern:

- **LLM Decision Node**: Analyzes the current state and decides whether to make tool calls or provide a final response.
- **Tool Execution Node**: Executes search tools when the LLM determines more information is needed.
- **Research Compression Node**: Summarizes and compresses research findings for efficient processing.
- **Routing Logic**: Determines workflow continuation based on LLM decisions.

### Context Engineering Strategy
We apply context engineering in two places following the principles outlined in Context Engineering for Agents:

#### 1. Webpage Content Summarization
Raw search results often contain excessive noise (navigation, ads, boilerplate content). Our `summarize_webpage_content()` function:

- Uses structured output to extract key information and relevant excerpts.
- Filters out irrelevant content while preserving factual details.
- Compresses lengthy articles into focused summaries.
- Maintains source attribution for credibility.

#### 2. Research Result Compression
As the agent performs multiple searches, the conversation context grows rapidly. Our `compress_research()` function:

- Synthesizes findings from multiple tool calls into cohesive insights.
- Extracts raw notes for detailed analysis while maintaining compressed summaries.
- Reduces token usage for subsequent LLM calls.
- Preserves essential information for report writing.

This dual-layer context engineering allows the agent to process extensive information efficiently while maintaining high-quality research output.

#### 3. Performing Careful Compression
Compression is risky! We need to be very careful about losing valuable information. We'll use an LLM for compression with instructions in a system prompt that comes before a potentially long, token-heavy trajectory of multiple tool calls. The long context can cause the compression LLM to lose sight of the task instructions, leading to generic summaries that lose information. So, we reinforce the compression task by adding a `compress_research_human_message` that:

- Explicitly restates the original research topic at compression time.
- Reminds the model to preserve ALL information relevant to the specific question.
- Emphasizes that comprehensive findings are critical for final report generation.
- Prevents task drift during the compression phase.

#### 4. Output Token Management
Research compression can generate long outputs. We need to ensure that they do not exceed model token limits, which can cause truncated responses that cut off mid-sentence (as seen with "**Sextant Coffee Ro" being cut off). As an example, GPT-4.1 has an output limit of up to 33k tokens and Claude4 sonnet supports 64k.

Model SDKs / LangChain integrations may cap this (e.g., to 1024 tokens in the case of Claude). Simply ensure that max tokens are set to ensure complete output. This prevents incomplete compression outputs and ensures full research findings are preserved. Test compression quality vs latency for different models.

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

