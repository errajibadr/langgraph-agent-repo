"""
Demonstration of the Generic React Agent System

This script shows how to use the new type-safe React Agent system with:
1. Generic type parameters
2. Proper type hints
3. Agent composition
4. Runtime type safety
"""

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from ai_engine.agents.react_agent import PydanticReactAgent, create_simple_agent
from ai_engine.agents.react_agent.examples.supervisor_agent import create_supervisor_agent
from ai_engine.agents.react_agent.examples.weather_agent import (
    InputWeatherAgentStatePydantic,
    OutputWeatherAgentStatePydantic,
    WeatherAgentStatePydantic,
    create_weather_agent,
)
from ai_engine.models.custom_chat_model import CustomChatModel


def demo_type_safety():
    """Demonstrate the type safety features of the generic React Agent."""
    print("\n🔒 TYPE SAFETY DEMONSTRATION")
    print("=" * 50)

    # Load environment
    load_dotenv()
    model = CustomChatModel(provider="groq")

    # 1. Create a weather agent with full type annotations
    print("\n1. Creating Weather Agent with Full Type Safety:")
    weather_agent: PydanticReactAgent[
        WeatherAgentStatePydantic, InputWeatherAgentStatePydantic, OutputWeatherAgentStatePydantic
    ] = create_weather_agent(model)

    print(f"   ✓ Weather agent created: {weather_agent.name}")
    print(f"   ✓ State schema: {weather_agent.state_schema.__name__}")
    print(f"   ✓ Input schema: {weather_agent.input_schema.__name__}")
    print(f"   ✓ Output schema: {weather_agent.output_schema.__name__}")
    print(f"   ✓ Tools count: {len(weather_agent.tools)}")

    # 2. Create a simple agent using the factory function
    print("\n2. Creating Simple Agent with Factory Function:")
    from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic

    from ai_engine.tools.reflection_tool import think_tool

    simple_agent = create_simple_agent(
        name="simple_agent",
        model=model,
        tools=[think_tool],
        state_schema=AgentStatePydantic,
    )

    print(f"   ✓ Simple agent created: {simple_agent.name}")
    print(f"   ✓ Uses same schema for input/output/state: {simple_agent.state_schema.__name__}")

    return weather_agent, simple_agent


def demo_agent_composition():
    """Demonstrate how agents can be composed together."""
    print("\n🏗️ AGENT COMPOSITION DEMONSTRATION")
    print("=" * 50)

    # Load environment
    load_dotenv()
    model = CustomChatModel(provider="groq")

    # Create weather agent
    print("\n1. Creating Weather Agent...")
    weather_agent = create_weather_agent(model)
    weather_graph = weather_agent.get_graph()
    print("   ✓ Weather agent graph compiled")

    # Create supervisor agent that uses weather agent
    print("\n2. Creating Supervisor Agent with Weather Tool...")
    supervisor_agent = create_supervisor_agent(model, weather_graph)
    supervisor_graph = supervisor_agent.get_graph()
    print("   ✓ Supervisor agent graph compiled")
    print("   ✓ Weather agent integrated as a tool")

    return supervisor_graph, weather_graph


def demo_runtime_validation():
    """Demonstrate runtime type validation."""
    print("\n🛡️ RUNTIME VALIDATION DEMONSTRATION")
    print("=" * 50)

    load_dotenv()
    model = CustomChatModel(provider="groq")

    # Test with valid schema
    print("\n1. Testing with Valid Schema:")
    try:
        weather_agent = create_weather_agent(model)
        print("   ✓ Schema validation passed")
    except Exception as e:
        print(f"   ❌ Schema validation failed: {e}")

    # Test with invalid schema (missing required fields)
    print("\n2. Testing with Invalid Schema:")
    from pydantic import BaseModel

    class InvalidSchema(BaseModel):
        # Missing required 'messages' and 'remaining_steps' fields
        some_field: str = "test"

    try:
        invalid_agent = PydanticReactAgent(
            name="invalid_agent",
            model=model,
            tools=[],
            state_schema=InvalidSchema,  # type: ignore
        )
        print("   ❌ Should have failed but didn't!")
    except ValueError as e:
        print(f"   ✓ Schema validation correctly failed: {e}")
    except Exception as e:
        print(f"   ⚠️ Unexpected error: {e}")


def demo_interactive_example():
    """Run an interactive example with the supervisor agent."""
    print("\n💬 INTERACTIVE EXAMPLE")
    print("=" * 50)

    load_dotenv()
    model = CustomChatModel(provider="groq")

    # Create the agent system
    weather_agent = create_weather_agent(model)
    weather_graph = weather_agent.get_graph()

    supervisor_agent = create_supervisor_agent(model, weather_graph)
    supervisor_graph = supervisor_agent.get_graph()

    print("\n🤖 Supervisor Agent is ready!")
    print("Ask me about the weather in any city...")
    print("(Type 'quit' to exit)")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        try:
            # Create input message
            from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic

            input_state = AgentStatePydantic(messages=[HumanMessage(user_input)])

            print("\n🤖 Agent:")

            # Stream the response
            for agent_name, mode, chunk in supervisor_graph.stream(
                input_state,
                config={"configurable": {"thread_id": "demo-thread"}},
                stream_mode=["values", "updates"],
                subgraphs=True,
            ):
                if mode == "values" and "messages" in chunk:
                    messages = chunk.get("messages", [])
                    if messages:
                        last_message = messages[-1]
                        if hasattr(last_message, "content") and last_message.content:
                            print(f"   {last_message.pretty_print()}")

        except KeyboardInterrupt:
            print("\n\n👋 Demo interrupted by user")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n👋 Demo completed!")


def main():
    """Run all demonstrations."""
    print("🚀 GENERIC REACT AGENT DEMONSTRATION")
    print("=" * 60)

    try:
        # Run demonstrations
        demo_type_safety()
        demo_agent_composition()
        demo_runtime_validation()

        # Ask if user wants interactive demo
        print("\n" + "=" * 60)
        response = input("Would you like to try the interactive demo? (y/n): ").strip().lower()

        if response in ["y", "yes"]:
            demo_interactive_example()
        else:
            print("👋 Demo completed!")

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
