"""Supervisor Agent Example - Demonstrates agent composition and tool usage."""

from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from langgraph.types import Command

from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.tools.reflection_tool import think_tool

from ..base import PydanticReactAgent, create_simple_agent
from ..types import DEFAULT_SYSTEM_PROMPT_TEMPLATE
from .weather_agent import InputWeatherAgentStatePydantic, create_weather_agent


def create_weather_tool(weather_graph):
    """Create a weather tool that uses the weather agent graph."""

    @tool
    def call_weather_agent(state: Annotated[AgentStatePydantic, InjectedState]) -> str:
        """
        Call the weather agent to get weather information from user messages.

        This tool invokes a specialized weather agent that can extract location information
        from user messages and provide weather data.

        Args:
            state: The current agent state containing user messages

        Returns:
            Weather summary information
        """
        try:
            response = weather_graph.invoke(
                InputWeatherAgentStatePydantic(
                    messages=[state.messages[0]],
                    query="Please find the weather from user messages",
                )
            )
            # Extract the summary from the response
            if hasattr(response, "summary"):
                return str(response.summary)
            elif isinstance(response, dict) and "summary" in response:
                return str(response["summary"])
            else:
                return str(response)
        except Exception as e:
            return f"Weather agent error: {str(e)}"

    return call_weather_agent


def create_supervisor_agent(
    model: CustomChatModel,
    weather_agent_graph,
    system_prompt_template: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE,
) -> PydanticReactAgent[AgentStatePydantic, AgentStatePydantic, AgentStatePydantic]:
    """
    Create a supervisor agent that can delegate to specialized agents.

    Args:
        model: The language model to use
        weather_agent_graph: Compiled weather agent graph
        system_prompt_template: Custom system prompt template

    Returns:
        Configured supervisor agent
    """
    # Create the weather tool with the graph
    weather_tool = create_weather_tool(weather_agent_graph)

    # Create supervisor agent using the simple factory
    return create_simple_agent(
        name="supervisor_agent",
        model=model,
        tools=[think_tool, weather_tool],
        state_schema=AgentStatePydantic,
        system_prompt_template=system_prompt_template,
    )


# Example usage and testing
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Create model
    model = CustomChatModel(provider="groq")

    # Create weather agent and its graph
    weather_agent = create_weather_agent(model)
    weather_graph = weather_agent.get_graph()

    # Create supervisor agent that can use the weather agent
    supervisor_agent = create_supervisor_agent(model, weather_graph)
    supervisor_graph = supervisor_agent.get_graph()

    # Test the supervisor agent
    first_message = AgentStatePydantic(messages=[HumanMessage("What's the weather in Paris?")])

    print("Testing Supervisor Agent with Weather Delegation:")
    print("=" * 50)

    last_message = None
    for agent_name, mode, chunk in supervisor_graph.stream(
        first_message,
        config={
            "configurable": {
                "thread_id": "thread-1",
                "project_name": "SupervisorWeatherTest",
                "metadata": {"user": "TestUser", "project_name": "SupervisorWeatherTest"},
                "langsmith_extra": {"project_name": "Supervisor Weather Test"},
            }
        },
        stream_mode=["values", "updates"],
        subgraphs=True,
    ):
        if mode == "values" and "messages" in chunk:
            messages = chunk.get("messages", [])
            if messages:
                message = messages[-1]
                if message != last_message:
                    print(f"\n--- Agent: {agent_name} ---")
                    last_message = message
                    chunk_without_messages = {k: v for k, v in chunk.items() if k != "messages"}
                    if chunk_without_messages:
                        print(f"State: {chunk_without_messages}")
                    print(f"Message: {message.pretty_print()}")

        elif mode == "updates" and "__interrupt__" in chunk:
            print(f"\nInterrupt: {chunk.get('__interrupt__')[0].value}")
            feedback = input("Your response: ") or "continue"
            for chunk in supervisor_graph.stream(
                Command(resume=feedback),
                config={"configurable": {"thread_id": "thread-1"}},
                stream_mode="values",
            ):
                if "messages" in chunk:
                    print(f"Resumed: {chunk.get('messages', [])[-1].pretty_print()}")

    print("\n" + "=" * 50)
    print("Test completed!")
