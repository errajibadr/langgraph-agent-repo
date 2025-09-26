"""Real streaming examples using the new modular streaming system.

Demonstrates actual LangGraph execution with streaming events,
not simulated data. Uses the supervisor graph for concrete examples.
"""

import asyncio
from typing import Any, Dict

from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.streaming.config import ChannelConfig, StreamMode, TokenStreamingConfig
from ai_engine.streaming.events import (
    ArtifactEvent,
    ChannelValueEvent,
    MessageReceivedEvent,
    TokenStreamEvent,
    ToolCallEvent,
)
from ai_engine.streaming.processor import ChannelStreamingProcessor
from langchain_core.messages import HumanMessage


async def real_supervisor_streaming_example():
    """Real supervisor graph streaming with the new modular system."""
    print("🚀 Real Supervisor Graph Streaming Example")
    print("=" * 50)

    # Configure channels to monitor
    channels = [
        ChannelConfig(key="messages", stream_mode=StreamMode.UPDATES_ONLY, parse_messages=True),
        ChannelConfig(key="notes", artifact_type="Document"),
        ChannelConfig(key="raw_notes", artifact_type="RawResearch"),
    ]

    # Configure token streaming with tool calls
    token_config = TokenStreamingConfig(
        enabled_namespaces={"main", "orchestrate", "orchestrator_tools"}, include_tool_calls=True
    )

    # Create processor
    processor = ChannelStreamingProcessor(
        channels=channels,
        token_streaming=token_config,
        prefer_updates=False,  # Use values for demo visibility
    )

    # Get real supervisor graph
    graph = get_supervisor_graph(name="streaming_supervisor_demo")

    # Real input
    input_data = {"messages": [HumanMessage(content="What's going on with my App Langgraph Platform? it lags.")]}
    config = {"configurable": {"thread_id": "supervisor_streaming_demo"}}
    context = {"user_id": "demo_user"}

    print("🔍 Starting real supervisor execution with streaming...")
    print(f"📊 Monitoring channels: {[c.key for c in channels]}")
    print(f"🎯 Token streaming from: {token_config.enabled_namespaces}")
    print(f"🔧 Tool calls enabled: {token_config.include_tool_calls}")
    print()

    # Track streaming statistics
    token_count = 0
    channel_updates = 0
    artifacts_created = 0
    tool_calls_seen = 0

    # Stream the real execution
    async for event in processor.stream(graph, input_data, config=config, context=context):
        if isinstance(event, TokenStreamEvent):
            token_count += 1
            if event.content_delta.strip():  # Only show non-empty tokens
                print(f"{event.content_delta}", end="| ", flush=True)

        elif isinstance(event, ChannelValueEvent):
            channel_updates += 1
            if event.channel == "messages" and event.value:
                latest_msg = event.value_delta
                if event.value_delta:  # Skip user input echo
                    print(
                        f"\n💬 [{event.namespace}] {event.value_delta[0].type}: {event.value_delta[0].content[:100]}..."
                    )

        elif isinstance(event, ArtifactEvent):
            artifacts_created += 1
            action = "Updated" if event.is_update else "Created"
            print(f"\n📄 [{event.namespace}] {action} {event.artifact_type}")
            print(f"    From channel '{event.channel}': {str(event.artifact_data)[:80]}...")

        elif isinstance(event, ToolCallEvent):
            if event.status == "started_streaming":
                tool_calls_seen += 1
                print(f"\n🔧 [{event.namespace}] Started Tool call #{tool_calls_seen}: {event.tool_name}")
            if event.status == "args_streaming":
                if event.args_delta.strip():
                    print(f"\n⚙️  [{event.namespace}] Tool args: {event.args_delta[:50]}...")
            if event.status == "completed_streaming":
                print(f"\n✅ [{event.namespace}] Tool completed: {event.tool_name}")
                print(f"    Args: {event.args}")
            if event.status == "result_received":
                print(f"\n✅ [{event.namespace}] Tool result: {event.result}")
            if event.status == "result_error":
                print(f"\n❌ [{event.namespace}] Tool error: {event.error}")

    print(f"\n\n📈 Streaming Summary:")
    print(f"   🎯 Tokens streamed: {token_count}")
    print(f"   📊 Channel updates: {channel_updates}")
    print(f"   📄 Artifacts created: {artifacts_created}")
    print(f"   🔧 Tool calls: {tool_calls_seen}")
    print("✅ Real supervisor streaming completed!")


async def message_deduplication_demo():
    """Demonstrate message parsing and deduplication."""
    print("🎯 Message Deduplication Demo")
    print("=" * 40)

    # Configure with both token streaming AND message parsing
    channels = [
        ChannelConfig(key="messages", parse_messages=True),  # Parse messages with deduplication
    ]

    token_config = TokenStreamingConfig(
        enabled_namespaces={"main"},  # Enable token streaming
        include_tool_calls=False,
    )

    processor = ChannelStreamingProcessor(
        channels=channels,
        token_streaming=token_config,
    )

    graph = get_supervisor_graph(name="dedup_demo")

    input_data = {"messages": [HumanMessage(content="Quick test for deduplication")]}

    print("🔍 This demo shows:")
    print("  1. Messages streamed token-by-token → TokenStreamEvent")
    print("  2. Same messages in channels → MessageReceivedEvent(was_streamed=True)")
    print("  3. ToolMessages only in channels → MessageReceivedEvent(was_streamed=False)")
    print()

    token_events = 0
    message_events = 0

    async for event in processor.stream(graph, input_data):
        if isinstance(event, TokenStreamEvent):
            token_events += 1

            print(f"'{event.content_delta}", end="| ")

        elif isinstance(event, MessageReceivedEvent):
            message_events += 1
            status = "🔄 DUPLICATE" if event.was_streamed else "🆕 NEW"
            print(
                f"\n💬 {status} {event.message_type}: {event.message.content[:50]}... (id: {getattr(event.message, 'id', None)})"
            )
    print(processor._seen_message_ids)
    print(f"\n📊 Result: {token_events} token events, {message_events} message events")
    print("✅ Deduplication demo completed!")


async def main():
    """Run all real streaming examples."""
    print("🚀 Real Streaming Examples with Supervisor Graph")
    print("=" * 55)

    try:
        # Load environment variables for the supervisor graph
        from dotenv import load_dotenv

        load_dotenv()

        # Run examples
        await real_supervisor_streaming_example()
        # await message_deduplication_demo()

        print("\n" + "=" * 55)
        print("✅ All real streaming examples completed successfully!")

    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("Make sure to install python-dotenv: pip install python-dotenv")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
    ###
