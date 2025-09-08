"""Research Agent Implementation.

This module implements a research agent that can perform iterative web searches
and synthesis to answer complex research questions.
"""

from ai_engine.agents.deep_research_agent.prompts.researcher_prompts import (
    compress_research_human_message,
    compress_research_system_prompt,
    research_agent_prompt,
)
from ai_engine.agents.deep_research_agent.research_agent_states import ResearcherOutputState, ResearcherState
from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.tools.reflection_tool import think_tool
from ai_engine.tools.research_tools import tavily_search
from ai_engine.utils.helpers import get_today_date
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, filter_messages
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import Literal

# ===== CONFIGURATION =====

# Set up tools and model binding
tools = [tavily_search, think_tool]
tools_by_name = {tool.name: tool for tool in tools}

# Initialize models
model = CustomChatModel(model="gpt-4.1-mini")
model_with_tools = model.bind_tools(tools)
summarization_model = CustomChatModel(model="gpt-4.1-mini")
compress_model = CustomChatModel(
    model="gpt-4.1", max_tokens=32000
)  # model="anthropic:claude-sonnet-4-20250514", max_tokens=64000

# ===== AGENT NODES =====


def llm_call(state: ResearcherState):
    """Analyze current state and decide on next actions.

    The model analyzes the current conversation state and decides whether to:
    1. Call search tools to gather more information
    2. Provide a final answer based on gathered information

    Returns updated state with the model's response.
    """
    return {
        "researcher_messages": [
            model_with_tools.invoke([SystemMessage(content=research_agent_prompt)] + state["researcher_messages"])
        ]
    }


def tool_node(state: ResearcherState):
    """Execute all tool calls from the previous LLM response.

    Executes all tool calls from the previous LLM responses.
    Returns updated state with tool execution results.
    """
    last_message = state["researcher_messages"][-1]
    tool_calls = last_message.tool_calls if isinstance(last_message, AIMessage) else []

    # Execute all tool calls
    observations = []
    for tool_call in tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observations.append(tool.invoke(tool_call["args"]))

    # Create tool message outputs
    tool_outputs = [
        ToolMessage(content=observation, name=tool_call["name"], tool_call_id=tool_call["id"])
        for observation, tool_call in zip(observations, tool_calls)
    ]

    return {"researcher_messages": tool_outputs}


def compress_research(state: ResearcherState) -> dict:
    """Compress research findings into a concise summary.

    Takes all the research messages and tool outputs and creates
    a compressed summary suitable for the supervisor's decision-making.
    """

    system_message = compress_research_system_prompt.format(date=get_today_date())
    messages = (
        [SystemMessage(content=system_message)]
        + state.get("researcher_messages", [])
        + [HumanMessage(content=compress_research_human_message)]
    )
    response = compress_model.invoke(messages)

    # Extract raw notes from tool and AI messages
    raw_notes = [str(m.content) for m in filter_messages(state["researcher_messages"], include_types=["tool", "ai"])]

    return {"compressed_research": str(response.content), "raw_notes": ["\n".join(raw_notes)]}


# ===== ROUTING LOGIC =====


def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """Determine whether to continue research or provide final answer.

    Determines whether the agent should continue the research loop or provide
    a final answer based on whether the LLM made tool calls.

    Returns:
        "tool_node": Continue to tool execution
        "compress_research": Stop and compress research
    """
    messages = state["researcher_messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, continue to tool execution
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"
    # Otherwise, we have a final answer
    return "compress_research"


def get_researcher_graph() -> CompiledStateGraph:
    # ===== GRAPH CONSTRUCTION =====

    # Build the agent workflow
    agent_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

    # Add nodes to the graph
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)
    agent_builder.add_node("compress_research", compress_research)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_node": "tool_node",  # Continue research loop
            "compress_research": "compress_research",  # Provide final answer
        },
    )
    agent_builder.add_edge("tool_node", "llm_call")  # Loop back for more research
    agent_builder.add_edge("compress_research", END)

    # Compile the agent
    researcher_agent = agent_builder.compile(name="researcher_graph")
    return researcher_agent


if __name__ == "__main__":
    research_brief = """
    What is the difference between fucntion and tool in langchain?
    """

    researcher_agent = get_researcher_graph()
    observation = researcher_agent.invoke({"researcher_messages": [HumanMessage(research_brief)]})
    print(observation)

    # for chunk in researcher_agent.stream(
    #     input={"researcher_messages": [HumanMessage(research_brief)]}, stream_mode="values"
    # ):
    #     print(chunk)
