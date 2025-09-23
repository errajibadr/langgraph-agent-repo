"""Example usage of the Deep Search Agent.

This example demonstrates how to use the deep search agent to disambiguate
user queries in an AI-OPS context.
"""

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage
from langgraph.graph import add_messages

from ai_engine.agents.aiops_deepsearch_agent.graphs.deepsearch_graph import get_deepsearch_graph
from ai_engine.agents.base.states.context import BaseContext


async def main():
    """Example usage of the clarify agent."""
    # Create the clarify graph
    deep_search_graph = get_deepsearch_graph(name="CustomDeepSearchAgent")

    # Configuration with thread ID for conversation tracking
    config = {"configurable": {"thread_id": "example-thread-1"}}
    context = BaseContext(user_id="example-user-1", model="openai/gpt-oss-20b")
    # Example user query that needs clarification
    initial_state = {
        "messages": [HumanMessage("Show me the recent issues with my app")],
        "artifacts": [],
    }

    # Stream the conversation
    print("=== Clarify Agent Example ===")

    async for chunk in deep_search_graph.astream(
        initial_state,
        config=config,  # type: ignore
        context=context,  # type: ignore
        stream_mode="values",
    ):
        if isinstance(chunk, dict):
            if "messages" in chunk and chunk["messages"]:
                last_message = chunk["messages"][-1]
                last_message.pretty_print()

            # Display artifacts if any
            if "artifacts" in chunk and chunk["artifacts"]:
                print("\n📋 Clarification Options:")
                for i, artifact in enumerate(chunk["artifacts"], 1):
                    print(f"  {i}. {artifact.title}")
                    print(f"     {artifact.description}")
                    print()


if __name__ == "__main__":
    import asyncio

    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
