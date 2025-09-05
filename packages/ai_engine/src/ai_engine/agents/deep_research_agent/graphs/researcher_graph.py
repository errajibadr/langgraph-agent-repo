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
from ai_engine.utils.dates import get_today_date
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, filter_messages
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
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
    researcher_agent = agent_builder.compile()
    return researcher_agent


if __name__ == "__main__":
    research_brief = """
    I want you to identify and rank the top 3 players in the Morocco men’s national football team (Al Mountakhab) by current form and last season performance, and produce a clear justification for the ranking. Use the instructions and defaults below unless I tell you otherwise. Required outputs: for each of the top 3 players provide (1) a short justification paragraph, (2) last completed club season summary (appearances, minutes, goals, assists, shots/90, goals/90, assists/90, key passes/90, xG, xA where available, successful dribbles/90, pass completion or progressive passes/90; for defenders: tackles/90, interceptions/90, clearances/90; for goalkeepers: saves, save%, clean sheets, goals prevented if available), (3) current form summary (last 10 club + country matches and last 6 months — match ratings where available, goals/assists/other key contributions per match, notes on minutes played and injuries), (4) a short note on competition level (league and continental competitions) and how that affects interpretation, and (5) direct source links for each key stat (prefer official/primary sources). Also provide a brief methodology section explaining how you combined “current form” and “last season stats” to produce the ranking, list of all data sources searched, and any caveats (injuries, recent transfers, small-sample noise).\n\nKey definitions and defaults (apply unless I specify otherwise):\n- \"Last season\": the most recently completed club season (default = 2024–25 season). If a player moved clubs mid-season, report combined totals and note the split by club.\n- \"Current form\": default = last 6 months and last 10 competitive matches across club and country (whichever gives more context). If you prefer a different window (e.g., last 5 matches or last 3 months), state it and justify.\n- Ranking method (default): produce a transparent composite ranking that weights current form and last season stats equally (50% current form, 50% last season). Show component scores (how each player scored on the two dimensions). If you believe a different weighting is more appropriate, say so and show the alternative ranking.\n\nMetrics to collect and normalize (adjust per position):\n- For attackers/midfielders: appearances, minutes, goals, assists, shots/90, goals/90, assists/90, key passes/90, xG, xA, successful dribbles/90, progressive carries/90 (if available), pass completion or progressive passes/90.\n- For defenders: appearances, minutes, tackles/90, interceptions/90, clearances/90, aerials won/90, passes out from back/progressive passes/90, clean sheets involvement.\n- For goalkeepers: appearances, minutes, saves, save%, clean sheets, goals prevented or post-shot xG if available.\n- For all: minutes per goal/assist, availability (injury absences), match ratings trends (WhoScored/SofaScore/FBref), and competition level (UEFA Champions League, top-5 league vs smaller leagues, CAF competitions).\n\nSource priorities (check these first and link specific pages):\n1) Official sources: Morocco FA (FRMF) match reports, player pages, club official sites, UEFA/CAF/league official stats pages.  \n2) Primary stat databases: Transfermarkt (appearances, minutes, transfers), FBref (per90 and advanced metrics), Opta/StatsBomb feeds where accessible, Understat for xG in supported leagues.  \n3) Match ratings & recent form: WhoScored, SofaScore, reputable press match reports (BBC, ESPN, L’Équipe, Marca).  \n4) For transfer/market context: Transfermarkt.  \n\nUnspecified aspects I did not assume and how you should treat them:\n- You did not specify the weighting between \"current form\" and \"last season\" — I defaulted to 50/50 but will adjust if you request.\n- You did not specify an exact time window for \"current form\" — I defaulted to last 6 months / last 10 matches; I will note this and can change it on request.\n- You did not require a position constraint; evaluate all Morocco senior squad players regardless of position.\n\nDeliverable format: rank list of top 3 (with composite score and component scores), per-player stat summary table, methodology, source links, and short caveats. Prioritize direct links to official club pages, FRMF, Transfermarkt and FBref pages for each player’s stats.
    """

    researcher_agent = get_researcher_graph()

    for chunk in researcher_agent.stream(
        input={"researcher_messages": [HumanMessage(research_brief)]}, stream_mode="values"
    ):
        print(chunk)
