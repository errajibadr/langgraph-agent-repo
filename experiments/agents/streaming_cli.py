"""Example usage of the Clarify Agent.

This example demonstrates how to use the clarify agent to disambiguate
user queries in an AI-OPS context.
"""

from operator import add
from typing import Annotated, TypedDict

from ai_engine.agents.aiops_deepsearch_agent.graphs.deepsearch_graph import get_deepsearch_graph
from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.clarify_agent.graphs.clarify_graph import get_clarify_graph
from ai_engine.agents.clarify_agent.states import ClarificationArtifact, ClarifyContext
from langchain_core.messages import AIMessageChunk, AnyMessage, BaseMessage, HumanMessage, ToolMessageChunk
from langgraph.graph import add_messages


class InputState(TypedDict):
    """Simple input state for the clarify agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


async def main():
    """Example usage of the clarify agent."""
    # Create the clarify graph
    deepsearch_graph = get_supervisor_graph(name="deepsearch_agent")

    # Configuration with thread ID for conversation tracking
    config = {"configurable": {"thread_id": "example-thread-1"}}
    context = ClarifyContext(user_id="example-user-1")  # type: ignore
    # Example user query that needs clarification
    initial_state = InputState(
        messages=[
            HumanMessage(
                "Show me the recent issues with my app. Before answering, think about a plan first please and then act by using the 'think' tool."
            )
        ]
    )

    # Stream the conversation
    print("=== Clarify Agent Example ===")

    async for data in deepsearch_graph.astream(
        initial_state,
        config=config,  # type: ignore
        context={**context, "model": "openai/gpt-oss-20b"},  # type: ignore
        stream_mode="messages",  # , "values"],
        # subgraphs=True,
    ):
        # print(data)

        # print(f"mode: {mode}")
        # # print(f"data: {data}")
        chunk, metadata = data
        # print(chunk)
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            print(f"chunk: {chunk.tool_calls}")
        if chunk.content:
            if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                print(f"chunk: {chunk.tool_call_chunks}")

        # node_name, state_update = next(iter(data.items()))
        # print(f"node_name: {node_name}")
        # print(f"state_update: {state_update}")
        # if isinstance(data, dict):
        #     if "messages" in data and data["messages"]:
        #         last_message = data["messages"][-1]
        #         last_message.pretty_print()

        #     # Display artifacts if any
        #     if "artifacts" in data and data["artifacts"]:
        #         print("\n📋 Clarification Options:")
        #         for i, artifact in enumerate(data["artifacts"], 1):
        #             print(f"  {i}. {artifact.title}")
        #             print(f"     {artifact.description}")
        #             print()


if __name__ == "__main__":
    import asyncio

    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
