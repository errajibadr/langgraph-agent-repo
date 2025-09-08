import asyncio
from typing import Literal, cast

from ai_engine.agents.deep_research_agent.graphs.researcher_graph import get_researcher_graph
from ai_engine.agents.deep_research_agent.prompts.supervisor_prompt import LEAD_RESEARCHER_PROMPT
from ai_engine.agents.deep_research_agent.supervisor_state import (
    ConductResearch,
    ResearchComplete,
    SupervisorOutputState,
    SupervisorState,
)
from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.tools.reflection_tool import think_tool
from ai_engine.utils.helpers import get_notes_from_tool_calls, get_today_date
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.types import Command

supervisor_model = CustomChatModel(model="gpt-4.1-mini").bind_tools([ConductResearch, ResearchComplete, think_tool])

# System constants
# Maximum number of tool call iterations for individual researcher agents
# This prevents infinite loops and controls research depth per topic
max_researcher_iterations = 6  # Calls to think_tool + ConductResearch

# Maximum number of concurrent research agents the supervisor can launch
# This is passed to the lead_researcher_prompt to limit parallel research tasks
max_concurrent_researchers = 3


async def supervisor(state: SupervisorState) -> Command[Literal["supervisor_tools"]]:
    """Supervisor agent"""

    system_message = LEAD_RESEARCHER_PROMPT.format(
        date=get_today_date(),
        max_researcher_iterations=max_researcher_iterations,
        max_concurrent_research_units=max_concurrent_researchers,
    )

    messages = [SystemMessage(content=system_message)] + state["supervisor_messages"]
    response = await supervisor_model.ainvoke(messages)

    return Command(
        goto="supervisor_tools",
        update={"supervisor_messages": [response], "research_iterations": state.get("research_iterations", 0) + 1},
    )


async def supervisor_tools(state: SupervisorState) -> Command[Literal["supervisor"] | Literal["__end__"]]:
    """Execute supervisor decisions - either conduct research or end the process.

    Handles:
    - Executing think_tool calls for strategic reflection
    - Launching parallel research agents for different topics
    - Aggregating research results
    - Determining when research is complete

    Args:
        state: Current supervisor state with messages and iteration count

    Returns:
        Command to continue supervision, end process, or handle errors
    """
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message: AIMessage = cast(AIMessage, supervisor_messages[-1])

    # Initialize variables for single return pattern
    tool_messages = []
    all_raw_notes = []
    next_step = "supervisor"  # Default next step
    should_end = False

    # Check exit criteria first
    exceeded_iterations = research_iterations >= max_researcher_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete = any(tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls)

    if exceeded_iterations or no_tool_calls or research_complete:
        should_end = True
        next_step = END
    else:
        # Execute ALL tool calls before deciding next step
        try:
            # Separate think_tool calls from ConductResearch calls
            think_tool_calls = [
                tool_call for tool_call in most_recent_message.tool_calls if tool_call["name"] == "think_tool"
            ]

            conduct_research_calls = [
                tool_call for tool_call in most_recent_message.tool_calls if tool_call["name"] == "ConductResearch"
            ]

            # Handle think_tool calls (synchronous)
            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(content=observation, name=tool_call["name"], tool_call_id=tool_call["id"])
                )

            if conduct_research_calls:
                async_tasks = []
                for search_call in conduct_research_calls:
                    research_agent = get_researcher_graph()
                    print(f"Launching research agent for {search_call['args']}")
                    async_tasks.append(
                        research_agent.ainvoke(
                            input={
                                "researcher_messages": [HumanMessage(search_call["args"]["research_topic"])],
                                "research_topic": search_call["args"]["research_topic"],
                            }
                        )
                    )

                observations = await asyncio.gather(*async_tasks)
                for search_call, observation in zip(conduct_research_calls, observations):
                    tool_messages.append(
                        ToolMessage(
                            content=observation.get("compressed_research", "Error Synthetizing Research"),
                            name=search_call["name"],
                            tool_call_id=search_call["id"],
                        )
                    )
                    all_raw_notes.append(observation.get("raw_notes", "Error Synthetizing Research"))

        except Exception as e:
            print(f"Error in supervisor tools: {e}")
            should_end = True
            next_step = END

    if should_end:
        return Command(  # type: ignore
            goto=next_step,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", ""),
            },
        )
    else:
        return Command(goto=next_step, update={"supervisor_messages": tool_messages, "raw_notes": all_raw_notes})  # type: ignore


def get_supervisor_graph() -> CompiledStateGraph:
    return (
        StateGraph(SupervisorState, output_schema=SupervisorOutputState)
        .add_node("supervisor", supervisor)
        .add_node("supervisor_tools", supervisor_tools)
        .add_edge(START, "supervisor")
    ).compile()


async def main():
    supervisor_agent = get_supervisor_graph()
    research_brief = """
    What is the difference between function and tool in langchain?
    """
    async for chunk in supervisor_agent.astream(
        input={"supervisor_messages": [HumanMessage(research_brief)]}, stream_mode="values"
    ):
        print(chunk.get("supervisor_messages", [])[-1].pretty_print())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
