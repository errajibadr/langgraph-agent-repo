"""Clarify Graph implementation.

This module contains the main graph factory function for creating
clarification workflows that help disambiguate user queries.
"""

from datetime import datetime
from typing import Callable, Literal, Type, cast

from ai_engine.agents.aiops_deepsearch_agent.states import GlobalState
from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.aiops_supervisor_agent.states import SupervisorContext, SupervisorState
from ai_engine.agents.base.states.context import BaseContext
from ai_engine.agents.clarify_agent.graphs.clarify_graph import get_clarify_graph
from ai_engine.utils.streaming_parser import create_console_parser
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel.main import asyncio


def get_deepsearch_graph(
    state_schema: type[GlobalState] = GlobalState,
    input_schema: Type[GlobalState] | None = None,
    output_schema: Type[GlobalState] | None = None,
    context_schema: Type[BaseContext] | None = BaseContext,
    *,
    name: str | None = None,
    include_clarify: bool | Callable = True,
    system_prompt: str | None = None,
    max_iterations: int = 3,
    force_thinking: bool = False,
    **kwargs,
) -> CompiledStateGraph[GlobalState, BaseContext, GlobalState, GlobalState]:
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

    # Build the graph
    graph = StateGraph(
        state_schema=state_schema, input_schema=input_schema, output_schema=output_schema, context_schema=context_schema
    )

    clarify = get_clarify_graph(
        name="ClarifyAgent", is_subgraph=True, parent_next_node="orchestrate", research_brief=True
    )
    if not include_clarify:
        clarify = lambda x: x
    supervisor = get_supervisor_graph(name="SupervisorAgent")

    # Add nodes
    graph.add_node("clarify", clarify)
    graph.add_node("orchestrate", supervisor)

    # Add edges
    graph.add_edge(START, "clarify")
    graph.add_edge("clarify", "orchestrate")
    # Compile and return
    compiled_graph = graph.compile(name=name or "DeepSearchAgent", **kwargs)
    return compiled_graph


async def main():
    from dotenv import load_dotenv

    load_dotenv()
    """Demonstrate streaming parser with supervisor graph."""
    graph = get_deepsearch_graph(name="steam_deepsearch_graph")
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
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
    asyncio.run(main())
