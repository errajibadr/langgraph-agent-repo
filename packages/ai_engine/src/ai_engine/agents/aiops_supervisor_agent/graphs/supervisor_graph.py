"""Clarify Graph implementation.

This module contains the main graph factory function for creating
clarification workflows that help disambiguate user queries.
"""

from datetime import datetime
from typing import Literal, Type, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel.main import asyncio
from langgraph.runtime import Runtime
from langgraph.types import Command

from ai_engine.agents.aiops_supervisor_agent.prompts.supervisor_prompts import SUPERVISOR_AIOPS_PROMPT
from ai_engine.agents.aiops_supervisor_agent.states import SupervisorContext, SupervisorState
from ai_engine.agents.aiops_supervisor_agent.tools.agent_tools import call_inspector_agent, call_navigator_agent
from ai_engine.agents.base.utils import get_user_context
from ai_engine.models.custom_chat_model import create_chat_model
from ai_engine.tools.reflection_tool import think_tool
from ai_engine.utils.streaming_parser import create_console_parser

supervisor_tools_list = {
    call_inspector_agent.name: call_inspector_agent,
    call_navigator_agent.name: call_navigator_agent,
    think_tool.name: think_tool,
}


# System constants
# Maximum number of tool call iterations for individual researcher agents
# This prevents infinite loops and controls research depth per topic
max_researcher_iterations = 7  # Calls to think_tool + ConductResearch

# Maximum number of concurrent research agents the supervisor can launch
# This is passed to the lead_researcher_prompt to limit parallel research tasks
max_concurrent_researchers = 3


async def supervisor_tools(
    state: SupervisorState, runtime: Runtime[SupervisorContext]
) -> Command[Literal["orchestrate"] | Literal["__end__"]]:
    """Execute supervisor decisions - either conduct research or end the process.
    Handles:
    - Executing think_tool calls for strategic reflection
    - Launching parallel research agents for different topics
    - Aggregating research results
    - Determining when research is complete
    """

    messages = state.get("messages", [])
    research_iteration = state.get("research_iteration", 0)
    most_recent_message: AIMessage = cast(AIMessage, messages[-1])

    # Initialize variables for single return pattern
    tool_messages = []
    all_raw_notes = []
    next_step = "orchestrate"  # Default next step
    should_end = False

    # Check exit criteria first
    exceeded_iterations = research_iteration >= max_researcher_iterations
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

            # Handle think_tool calls (synchronous)
            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(content=observation, name=tool_call["name"], tool_call_id=tool_call["id"])
                )

            investigation_calls = [
                tool_call for tool_call in most_recent_message.tool_calls if tool_call["name"] != "think_tool"
            ]

            if investigation_calls:
                async_tasks = []
                for investigation_call in investigation_calls:
                    print(f"Launching {investigation_call['name']} tool for {investigation_call['args']}")
                    async_tasks.append(
                        supervisor_tools_list[investigation_call["name"]].ainvoke(
                            input={
                                "app": investigation_call["args"]["app"],
                                "query": investigation_call["args"]["query"],
                            }
                        )
                    )
                observations = await asyncio.gather(*async_tasks)

                for investigation_call, observation in zip(investigation_calls, observations):
                    tool_messages.append(
                        ToolMessage(
                            content=observation, name=investigation_call["name"], tool_call_id=investigation_call["id"]
                        )
                    )
                    all_raw_notes.append(observation)
        except Exception as e:
            print(f"Error in supervisor tools: {e}")
            should_end = True
            next_step = END
    if should_end:
        return Command(  # type: ignore
            goto=next_step,
            update={
                "notes": state.get("notes", []) + all_raw_notes,
            },
        )
    else:
        return Command(
            goto=next_step,
            update={
                "messages": tool_messages,
                "raw_notes": all_raw_notes,
                "research_iteration": research_iteration + 1,
            },
        )  # type: ignore


def get_supervisor_graph(
    state_schema: type[SupervisorState] = SupervisorState,
    input_schema: Type[SupervisorState] | None = None,
    output_schema: Type[SupervisorState] | None = None,
    context_schema: Type[SupervisorContext] | None = SupervisorContext,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    max_iterations: int = 3,
    force_thinking: bool = False,
    **kwargs,
) -> CompiledStateGraph[SupervisorState, SupervisorContext, SupervisorState, SupervisorState]:
    """Create a clarify graph for disambiguating user queries.

    This factory function creates a LangGraph workflow that helps clarify
    ambiguous user queries before routing them to specialist agents.

    Args:
        state_schema: The state schema type to use for the graph
        name: Optional name for the compiled graph
        system_prompt: Optional custom system prompt (defaults to CLARIFY_AIOPS_PROMPT)
        enrich_query_enabled: Whether to enable query enrichment node
        **kwargs: Additional arguments passed to graph.compile()

    Returns:
        Compiled state graph for clarification workflow
    """

    async def model_node(state: SupervisorState, runtime: Runtime[SupervisorContext]):
        """Main clarification node that processes user queries.

        This node uses an LLM to determine if clarification is needed
        and generates appropriate questions or verification messages.
        """

        context = runtime.context or {}
        runtime_prompt = context.get("supervisor_system_prompt", "") if runtime.context else ""
        user_id = context.get("user_id", None)
        user_context = get_user_context(user_id)
        model = context.get("model", None)
        supervisor_model = create_chat_model(model=model).bind_tools(list(supervisor_tools_list.values()))

        print(f"iteration: {state.get('research_iteration', 0)}")
        # Prepare template parameters with defaults
        params = {"current_date": datetime.now().strftime("%Y-%m-%d"), "user_context": user_context}

        prompt_template = runtime_prompt or system_prompt or SUPERVISOR_AIOPS_PROMPT.format(**params)
        system_message = SystemMessage(content=prompt_template)
        supervisor_response = await supervisor_model.ainvoke([system_message] + state.get("messages", []))

        return {"messages": [supervisor_response]}

    # Build the graph
    graph = StateGraph(
        state_schema=state_schema, input_schema=input_schema, output_schema=output_schema, context_schema=context_schema
    )

    # Add nodes
    graph.add_node("orchestrate", model_node)
    graph.add_node("orchestrator_tools", supervisor_tools)

    # Add edges
    graph.add_edge(START, "orchestrate")
    graph.add_edge("orchestrate", "orchestrator_tools")

    # Compile and return
    compiled_graph = graph.compile(name=name or "OrchestratorAgent", **kwargs)
    return compiled_graph


async def main():
    from dotenv import load_dotenv

    load_dotenv()
    """Demonstrate streaming parser with supervisor graph."""
    graph = get_supervisor_graph(name="supervisor_graph")
    config = {"configurable": {"thread_id": "thread-1"}}

    # Create streaming parser with console output
    parser = create_console_parser()

    print("🚀 Starting Supervisor Agent with Streaming Parser")
    print("=" * 60)

    async for mode, chunk in graph.astream(
        {"messages": [HumanMessage(content="What's going on with my App Langgraph Platform? it lags")]},  # type: ignore
        config=config,  # type: ignore
        context=SupervisorContext(user_id="h88214"),  # type: ignore
        stream_mode=["messages", "values"],
    ):
        if mode == "messages":
            chunk_messages, config = chunk
            # Process the chunk through our streaming parser if it's a BaseMessage
            if isinstance(chunk_messages, BaseMessage):
                parser.process_chunk(chunk_messages)

    print("\n" + "=" * 60)
    print("🏁 Streaming Complete!")
    print(f"Final state: {parser.get_current_state()}")
    print(f"Final tool calls: {parser.get_final_tool_calls()}")


if __name__ == "__main__":
    asyncio.run(main())
