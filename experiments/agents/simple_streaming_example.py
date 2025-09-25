"""Simple example of channel-based streaming.

This example shows how to use the new ChannelStreamingProcessor
to handle complex streaming scenarios with multiple namespaces,
artifacts, and parallel subgraph execution.
"""

import asyncio

from ai_engine.agents.aiops_deepsearch_agent.graphs.deepsearch_graph import get_deepsearch_graph
from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.utils.channel_streaming_v2 import (
    ArtifactStreamEvent,
    ChannelConfig,
    ChannelStreamingProcessor,
    StreamMode,
    TokenStreamEvent,
    UpdateStreamEvent,
    ValueStreamEvent,
)
from langchain_core.messages import HumanMessage


async def main():
    """Example usage of the channel streaming processor."""

    # Configure channels for your complex scenario
    channels = [
        # Stream messages token-by-token from main namespace and clarify subgraphs
        ChannelConfig(
            key="messages",
            stream_mode=StreamMode.TOKEN_BY_TOKEN,
            namespaces={"main", "clarify"},  # Only these namespaces stream tokens
            # message_tags={"agent_name"},  # Filter by agent tags
        ),
        # Capture supervisor messages as updates only (faster)
        ChannelConfig(key="supervisor_messages", stream_mode=StreamMode.UPDATES_ONLY, namespaces={"main"}),
        # Map notes to document artifacts
        ChannelConfig(
            key="notes",
            stream_mode=StreamMode.VALUES_ONLY,
            artifact_type="Document",
            filter_fn=lambda x: x is not None and len(str(x)) > 5,  # Skip empty notes
        ),
        # Map questions to clarification artifacts
        ChannelConfig(key="questions", stream_mode=StreamMode.VALUES_ONLY, artifact_type="UserClarification"),
        # Track any artifacts generated
        ChannelConfig(key="artifacts", stream_mode=StreamMode.VALUES_ONLY, artifact_type="GeneratedArtifact"),
    ]

    # Create processor with preference for updates (faster)
    processor = ChannelStreamingProcessor(channels, prefer_updates=True)

    # Get your graph
    graph = get_supervisor_graph(name="supervisor_agent")

    # Input data
    input_data = {"messages": [HumanMessage("Show me the recent issues with my app")]}

    # Configuration
    config = {"configurable": {"thread_id": "example-thread-1"}}

    print("=== Channel-Based Streaming Example ===\n")

    # Stream with the processor
    async for event in processor.stream(graph, input_data, config=config):
        # Handle different event types
        if isinstance(event, TokenStreamEvent):
            # Token-by-token content from specified namespaces
            print(f"[{event.node_name}:{event.task_id}] 💬 {event.content_delta}", end="", flush=True)

        elif isinstance(event, ArtifactStreamEvent):
            # Artifacts mapped from state keys
            print(f"\n[{event.node_name}] 📋 {event.artifact_type}: {event.artifact_data}")
            if event.task_id:
                print(f"  Task ID: {event.task_id}")

        elif isinstance(event, UpdateStreamEvent):
            # State updates (deltas)
            print(f"\n[{event.node_name}] 🔄 Update: {event.state_update}")

        elif isinstance(event, ValueStreamEvent):
            # Other state value updates
            print(f"\n[{event.node_name}] 🔄 {event.channel} updated: {event.value}")
            if event.value_delta:
                print(f"  Delta: {event.value_delta}")

    print("\n\n=== Streaming Complete ===")


async def simple_example():
    """Even simpler example for basic usage."""

    # Just use defaults - messages token-by-token, artifacts as values
    processor = ChannelStreamingProcessor(
        [
            ChannelConfig(
                key="messages",
                stream_mode=StreamMode.TOKEN_BY_TOKEN,
                namespaces={"main"},  # Only main namespace
            )
        ]
    )

    # Your graph and input
    graph = get_deepsearch_graph(name="simple_agent", include_clarify=False)
    input_data = {"messages": [HumanMessage("Hello")]}

    print("=== Simple Streaming ===\n")

    async for event in processor.stream(graph, input_data):
        if isinstance(event, TokenStreamEvent):
            print(event.content_delta, end="", flush=True)
        elif isinstance(event, ValueStreamEvent):
            print(f"\n[State Update] {event.channel}: {event.value}")

    print("\n")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Run the complex example
    asyncio.run(main())

    # Or run the simple example
    # asyncio.run(simple_example())
