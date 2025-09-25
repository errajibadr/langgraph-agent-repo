"""Example demonstrating streaming tool call parsing with LangGraph.

This example shows how to use the StreamingGraphParser to handle
progressive tool call streaming from LangGraph agents.
"""

import asyncio

from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.aiops_supervisor_agent.states import SupervisorContext
from ai_engine.utils.streaming_parser import StreamingGraphParser, create_console_parser
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage


async def demonstrate_streaming_parsing():
    """Demonstrate the streaming parser with a supervisor graph."""
    print("🚀 LangGraph Streaming Parser Demo")
    print("=" * 60)

    # Create the supervisor graph
    graph = get_supervisor_graph(name="streaming_demo")
    config = {"configurable": {"thread_id": "demo-thread"}}

    # Create streaming parser with console output
    parser = create_console_parser(enable_tool_streaming=False, enable_content_streaming=True)

    print("\n📝 Query: 'What's going on with my App Langgraph Platform? it lags'")
    print("-" * 60)

    # Stream the graph execution
    async for mode, chunk in graph.astream(
        {"messages": [HumanMessage(content="What's going on with my App Langgraph Platform? it lags")]},
        config=config,
        context=SupervisorContext(user_id="demo-user"),
        stream_mode=["messages", "values"],
    ):
        if mode == "messages":
            chunk_messages, config = chunk
            # Process through our streaming parser
            if hasattr(chunk_messages, "content") or hasattr(chunk_messages, "tool_calls"):
                parser.process_chunk(chunk_messages)

    print("\n" + "=" * 60)
    print("🏁 Streaming Complete!")

    # Show final state
    final_state = parser.get_current_state()
    print(f"\n📊 Final Content Length: {len(final_state.content)}")
    print(f"🔧 Total Tool Calls: {len(final_state.tool_calls)}")

    # Show completed tool calls
    completed_calls = parser.get_final_tool_calls()
    if completed_calls:
        print("\n✅ Completed Tool Calls:")
        for i, call in enumerate(completed_calls, 1):
            print(f"  {i}. {call['name']} - {call['args']}")

    return parser


async def demonstrate_custom_parser():
    """Demonstrate creating a custom parser with specific callbacks."""
    print("\n🎨 Custom Parser Demo")
    print("=" * 40)

    # Track statistics
    stats = {"content_updates": 0, "tool_calls_started": 0, "tool_calls_completed": 0, "total_args_length": 0}

    def on_content_update(content: str):
        stats["content_updates"] += 1
        print(f"📝 Content Update #{stats['content_updates']}: {len(content)} chars")

    def on_tool_call_start(idx: int, name: str, call_id: str):
        stats["tool_calls_started"] += 1
        print(f"🔧 Tool Call Started: {name} (Index: {idx})")

    def on_tool_call_update(idx: int, state):
        stats["total_args_length"] = max(stats["total_args_length"], len(state.accumulated_args))
        print(f"🔄 Tool Call {idx} Update: {len(state.accumulated_args)} chars accumulated")

    def on_tool_call_complete(idx: int, state):
        stats["tool_calls_completed"] += 1
        print(f"✅ Tool Call {idx} Complete: {state.name}")

    # Create custom parser
    parser = StreamingGraphParser(
        on_content_update=on_content_update,
        on_tool_call_start=on_tool_call_start,
        on_tool_call_update=on_tool_call_update,
        on_tool_call_complete=on_tool_call_complete,
    )

    # Use the parser (simplified example)
    graph = get_supervisor_graph(name="custom_demo")
    config = {"configurable": {"thread_id": "custom-thread"}}

    async for mode, chunk in graph.astream(
        {"messages": [HumanMessage(content="Check the status of my applications")]},
        config=config,
        context=SupervisorContext(user_id="custom-user"),
        stream_mode=["messages"],
    ):
        if mode == "messages":
            chunk_messages, config = chunk
            if hasattr(chunk_messages, "content") or hasattr(chunk_messages, "tool_calls"):
                parser.process_chunk(chunk_messages)

    print("\n📊 Final Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return parser, stats


if __name__ == "__main__":

    async def main():
        # Run the basic demonstration
        await demonstrate_streaming_parsing()

        # Run the custom parser demonstration
        # await demonstrate_custom_parser()

        # # Run the streaming control demonstration
        # await demonstrate_streaming_control()

        print("\n🎉 All demonstrations completed!")

    asyncio.run(main())
