"""Simple example using the corrected channel-based streaming processor.

This example demonstrates the proper separation between:
1. Channel streaming: Monitor state keys (messages, notes, etc.) via values/updates
2. Token streaming: Stream LLM output token-by-token from specific namespaces
"""

import asyncio

from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.utils.channel_streaming_v2 import (
    ArtifactEvent,
    ChannelConfig,
    ChannelStreamingProcessor,
    ChannelUpdateEvent,
    ChannelValueEvent,
    StreamMode,
    TokenStreamEvent,
    TokenStreamingConfig,
)
from langchain_core.messages import HumanMessage


async def main():
    """Example usage of the corrected channel streaming processor."""

    print("=== Corrected Channel-Based Streaming Example ===\n")

    # 1. Configure state channels to monitor (always values/updates)
    channels = [
        # Monitor messages state across all namespaces
        ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY),
        # Monitor supervisor messages with updates for faster streaming
        ChannelConfig(key="supervisor_messages", stream_mode=StreamMode.UPDATES_ONLY),
        # Map notes to document artifacts with filtering
        ChannelConfig(
            key="notes",
            artifact_type="Document",
            filter_fn=lambda x: x is not None and len(str(x)) > 5,  # Skip empty notes
        ),
        # Map questions to clarification artifacts
        ChannelConfig(key="questions", artifact_type="UserClarification"),
    ]

    # 2. Configure token streaming from specific namespaces only
    token_config = TokenStreamingConfig(
        enabled_namespaces={"main", "clarify"},  # Only stream tokens from these namespaces
        # message_tags={"agent_name"}  # Uncomment to filter by agent tags
    )

    # 3. Create processor with separated concerns
    processor = ChannelStreamingProcessor(
        channels=channels,  # What state keys to monitor
        token_streaming=token_config,  # Which namespaces stream tokens
        prefer_updates=True,  # Use updates for faster state streaming
    )

    # 4. Get your graph and input
    graph = get_supervisor_graph(name="supervisor_agent")
    input_data = {
        "messages": [
            HumanMessage(
                "are there any issues with Langgraph Platform it's laggy ? think about a plan first please and then act "
            )
        ]
    }
    config = {"configurable": {"thread_id": "example-thread-1"}}

    print("🔧 Configuration:")
    print(f"  📊 Monitoring channels: {[c.key for c in channels]}")
    print(f"  🎯 Token streaming from: {token_config.enabled_namespaces}")
    print(f"  ⚡ Using updates mode: {processor.prefer_updates}")
    print()

    # 5. Stream with the processor
    token_count = 0
    channel_updates = 0
    artifacts_created = 0

    async for event in processor.stream(graph, input_data, config=config):
        # Handle token-by-token streaming from enabled namespaces
        if isinstance(event, TokenStreamEvent):
            token_count += 1
            print(f"🎯 [{event.namespace}] {event.content_delta}", end="", flush=True)
            if event.node_name and event.node_name != event.namespace:
                print(f" (from {event.node_name})", end="", flush=True)

        # Handle state channel value updates
        elif isinstance(event, ChannelValueEvent):
            channel_updates += 1
            print(f"\n📊 [{event.namespace}] Channel '{event.channel}' updated")
            if isinstance(event.value, list) and len(event.value) > 0:
                print(f"    Latest: {str(event.value[-1])[:100]}...")
            else:
                print(f"    Value: {str(event.value)[:100]}...")
            if event.value_delta:
                print(f"    Delta: {str(event.value_delta)[:50]}...")

        # Handle state channel update deltas
        elif isinstance(event, ChannelUpdateEvent):
            channel_updates += 1
            print(f"\n⚡ [{event.namespace}] Update from {event.node_name}")
            print(f"    Channel '{event.channel}': {str(event.state_update)[:100]}...")

        # Handle artifacts mapped from state channels
        elif isinstance(event, ArtifactEvent):
            artifacts_created += 1
            action = "Updated" if event.is_update else "Created"
            print(f"\n📋 [{event.namespace}] {action} {event.artifact_type}")
            print(f"    From channel '{event.channel}': {str(event.artifact_data)[:100]}...")

    print(f"\n\n✅ Streaming Complete!")
    print(f"   🎯 Tokens streamed: {token_count}")
    print(f"   📊 Channel updates: {channel_updates}")
    print(f"   📋 Artifacts created: {artifacts_created}")


async def simple_example():
    """Even simpler example with minimal configuration."""

    print("=== Simple Streaming Example ===\n")

    # Just monitor messages and stream tokens from main namespace
    processor = ChannelStreamingProcessor(
        channels=[ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY)],
        token_streaming=TokenStreamingConfig(enabled_namespaces={"main"}),
    )

    # Use a simple graph
    from ai_engine.agents.aiops_deepsearch_agent.graphs.deepsearch_graph import get_deepsearch_graph

    graph = get_deepsearch_graph(name="simple_agent", include_clarify=False)
    input_data = {"messages": [HumanMessage("Hello, how are you?")]}

    async for event in processor.stream(graph, input_data):
        if isinstance(event, TokenStreamEvent):
            print(event.content_delta, end="", flush=True)
        elif isinstance(event, ChannelValueEvent):
            print(f"\n📊 Messages updated: {len(event.value)} total messages")

    print("\n✅ Simple streaming complete!")


async def namespace_demonstration():
    """Demonstrate namespace-based token streaming."""

    print("=== Namespace Demonstration ===\n")

    # Configure to stream tokens from multiple namespaces
    processor = ChannelStreamingProcessor(
        channels=[ChannelConfig(key="messages", stream_mode=StreamMode.VALUES_ONLY)],
        token_streaming=TokenStreamingConfig(
            enabled_namespaces={"main", "clarify", "supervisor"}  # Multiple namespaces
        ),
    )

    # Use supervisor graph which has multiple namespaces
    graph = get_supervisor_graph(name="multi_namespace_demo")
    input_data = {"messages": [HumanMessage("Analyze the system performance issues")]}

    namespaces_seen = set()

    async for event in processor.stream(graph, input_data):
        if isinstance(event, TokenStreamEvent):
            namespaces_seen.add(event.namespace)
            print(f"[{event.namespace}] {event.content_delta}", end="", flush=True)
        elif isinstance(event, ChannelValueEvent):
            print(f"\n📊 [{event.namespace}] Channel update: {event.channel}")

    print(f"\n\n✅ Namespaces that streamed tokens: {namespaces_seen}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Run the main example
    asyncio.run(main())

    print("\n" + "=" * 60 + "\n")

    # Run the simple example
    # asyncio.run(simple_example())

    # Run the namespace demonstration
    # asyncio.run(namespace_demonstration())
