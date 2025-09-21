"""Advanced example showing artifacts in action.

This example demonstrates a more realistic scenario where the clarify agent
generates artifacts that users can select from.
"""

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage
from langgraph.graph import add_messages

from ai_engine.agents.clarify_agent.graphs.clarify_graph import get_clarify_graph
from ai_engine.agents.clarify_agent.states import ClarificationArtifact


class InputState(TypedDict):
    """Input state for the clarify agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    current_round: int
    max_rounds: int
    artifacts: Annotated[list[ClarificationArtifact], add]


def simulate_user_selection(artifacts: list[ClarificationArtifact], choice_index: int) -> str:
    """Simulate user clicking on an artifact."""
    if 0 <= choice_index < len(artifacts):
        selected = artifacts[choice_index]
        print(f"✅ User selected: {selected.title}")
        print(f"   Description: {selected.description}")
        return selected.id
    return ""


def main():
    """Advanced example with artifact selection."""
    # Create the clarify graph with custom context
    clarify_graph = get_clarify_graph(
        state_schema=InputState,
        name="ClarifyAgentAdvanced",
        enrich_query_enabled=False,
    )

    # Configuration with context that will generate artifacts
    config = {
        "configurable": {
            "thread_id": "advanced-example-1",
            "user_id": "user123",
            "current_incidents_alerts": "2 critical alerts in production",
            "aiops_vocabulary": "Standard monitoring terminology",
        }
    }

    # Test different scenarios that should generate artifacts
    test_scenarios = [
        "Show me recent issues",
        "Check my app performance",
        "What's happening in production?",
        "Analyze the errors from today",
    ]

    for i, query in enumerate(test_scenarios, 1):
        print(f"\n{'=' * 50}")
        print(f"SCENARIO {i}: {query}")
        print("=" * 50)

        initial_state = InputState(
            messages=[HumanMessage(query)],
            current_round=0,
            max_rounds=3,
            artifacts=[],
        )

        # Stream the conversation
        artifacts_found = []
        for chunk in clarify_graph.stream(
            initial_state,
            config=config,  # type: ignore
            stream_mode="values",
        ):
            if isinstance(chunk, dict):
                if "messages" in chunk and chunk["messages"]:
                    last_message = chunk["messages"][-1]
                    print(f"\n🤖 Agent: {last_message.content}")

                # Collect and display artifacts
                if "artifacts" in chunk and chunk["artifacts"]:
                    artifacts_found = chunk["artifacts"]
                    print(f"\n📋 Generated {len(artifacts_found)} clarification options:")
                    for j, artifact in enumerate(artifacts_found, 1):
                        print(f"  {j}. [{artifact.id}] {artifact.title}")
                        print(f"     📝 {artifact.description}")
                        print()

        # Simulate user selection if artifacts were generated
        if artifacts_found:
            print("👤 User would click on option 1 in the frontend...")
            simulate_user_selection(artifacts_found, 0)
        else:
            print("ℹ️  No artifacts generated - query was clear enough")

        print("\n" + "-" * 50)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
