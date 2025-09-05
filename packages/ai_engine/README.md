### Context engineering

Overview
Our research agent perform iterative tool-calling to search for information.

The agent follows a simple yet effective pattern:

LLM Decision Node: Analyzes the current statwe and decides whether to make tool calls or provide a final response
Tool Execution Node: Executes search tools when the LLM determines more information is needed
Research Compression Node: Summarizes and compresses research findings for efficient processing
Routing Logic: Determines workflow continuation based on LLM decisions
Context Engineering Strategy
We apply context engineering in two places following the principles outlined in Context Engineering for Agents:

1. Webpage Content Summarization
Raw search results often contain excessive noise (navigation, ads, boilerplate content). Our summarize_webpage_content() function:

Uses structured output to extract key information and relevant excerpts
Filters out irrelevant content while preserving factual details
Compresses lengthy articles into focused summaries
Maintains source attribution for credibility
2. Research Result Compression
As the agent performs multiple searches, the conversation context grows rapidly. Our compress_research() function:

Synthesizes findings from multiple tool calls into cohesive insights
Extracts raw notes for detailed analysis while maintaining compressed summaries
Reduces token usage for subsequent LLM calls
Preserves essential information for report writing
This dual-layer context engineering allows the agent to process extensive information efficiently while maintaining high-quality research output.

3. Performing Careful Compression
Compression is risky! We need to be very careful about loosing valuable information. We'll use an LLM for compression with instructions in a system prompt that comes before a potentially long, token-heavy trajectory of multiple tool calls. The long context can cause the compression LLM to loose sight of the task instructions, leading to generic summaries that loose information. So, we reinforce the compression task by adding a compress_research_human_message that:

Explicitly restates the original research topic at compression time
Reminds the model to preserve ALL information relevant to the specific question
Emphasizes that comprehensive findings are critical for final report generation
Prevents task drift during the compression phase
4. Output Token Management
Research compression can generate long outputs. We need to sure that they do not exceed model token limits, which can cause truncated responses that cut off mid-sentence (as seen with "**Sextant Coffee Ro" being cut off). As an example, GPT-4.1 has output limit of up to 33k tokens and Claude4 sonnet supports 64k.

Model SDKs / LangChain integrations may cap this (e.g., to 1024 tokens in the case of Claude). Simply ensure that max tokens is set to ensure complete output. This prevents incomplete compression outputs and ensures full research findings are preserved. Test compression quality vs latency for different models. For example:


### LLM As A JUDGE Best Practices;

Now, we need to write an evaluator that will compare our research brief against the success criteria that we have specified for each example. For this, we'll use an LLM-as-judge. You can fine some useful tips for writing llm-as-judge evaluators here, which include:

Role Definition with Expertise Context

Defined specific expert roles ("research brief evaluator", "meticulous auditor")
Specialized the role to the specific evaluation domain
Clear Task Specification

Binary pass/fail judgments (avoiding complex multi-dimensional scoring)
Explicit task boundaries and objectives
Focus on actionable evaluation criteria
Rich Contextual Background

Provide domain-specific context about research brief quality
Explain the importance of accurate evaluation
Connect evaluation outcomes to downstream consequences
Structured XML Organization

Used semantic XML tags for different sections
Clear separation of role, task, context, inputs, guidelines, and outputs
Improved prompt parsing and comprehension
Comprehensive Guidelines with Examples

Detailed PASS/FAIL criteria with specific conditions
Multiple concrete examples showing correct judgments
3-4 examples per prompt covering different scenarios
Both positive and negative examples for each judgment type
Edge case handling and decision boundary clarification
Explicit Output Instructions

Clear guidance on how to apply the evaluation criteria
Instructions for handling ambiguous cases
Emphasis on consistency and systematic evaluation
Bias Reduction Techniques

"Strict but fair" guidance to balance precision and recall
"When in doubt, lean toward FAIL" for conservative evaluation
Systematic evaluation process to reduce subjective variation

### Research agent prompting best practices : 

#### Prompt
First, we'll define a prompt that instructs our agent to use available search tools.

To prevent excessive tool calls and maintain research focus, we use a few prompting techniques for agents:

1. Think Like The Agent
What instructions would you give a new work colleague?

Read the question carefully - What specific information does the user need?
Start with broader searches - Use broad, comprehensive queries first
After each search, pause and assess - Do I have enough to answer? What's still missing?
Execute narrower searches as you gather information - Fill in the gaps.
2. Concrete Heuristics (Prevent "Spin-Out" on excessive tool calls)
Use Hard Limits to prevent the research agent from calling tools excessively:

Stop when you can answer confidently - Don't keep searching for perfection.
Give it budgets - Use 2-3 search tool calls for simple queries. Use up to 5 for complex queries.
Limit - Always stop after 5 search tool calls if you cannot find the right source(s).
3. Show your thinking
After each search tool calling, use think_tool to analyze the results:

What key information did I find?
What's missing?
Do I have enough to answer the question comprehensively?
Should I search more or provide my answer?
Results
These techniques transform problematic research behavior like:

"best coffee shops SF" → "Saint Frank Coffee details" → "Sightglass Coffee details" → "Ritual Coffee details" → etc. (20+ searches)
Into efficient patterns like:

"best coffee shops SF" → ThinkTool(analyze results) → "SF specialty coffee quality ratings" → ThinkTool(assess completeness) → provide answer (3-5 searches total)
The key insight: Think like a human researcher with limited time - this prevents the "spin-out problem" where agents continue searching indefinitely.