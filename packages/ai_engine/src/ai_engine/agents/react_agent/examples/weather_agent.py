"""Weather Agent Example - Demonstrates type-safe React Agent usage."""

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from langgraph.prebuilt import InjectedState
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from ai_engine.models.custom_chat_model import CustomChatModel

from ..base import PydanticReactAgent
from ..types import DEFAULT_SYSTEM_PROMPT_TEMPLATE


# Weather-specific state schemas
class WeatherAgentStatePydantic(BaseModel):
    """The state of the weather agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    weather_messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)
    query: str | None = None
    remaining_steps: RemainingSteps = 5


class InputWeatherAgentStatePydantic(BaseModel):
    """The input state of the weather agent."""

    query: str
    messages: Annotated[Sequence[BaseMessage], add_messages]


class Summary(BaseModel):
    """Weather summary response format."""

    summary: str = Field(description="The summary of the weather, if unknown, should be specified")
    temperature: float | None = Field(
        default=None, description="The temperature of the weather; if unknown, should be None"
    )


class OutputWeatherAgentStatePydantic(BaseModel):
    """The output state of the weather agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: Summary


# Weather-specific tools
@tool
def get_weather(city: str) -> str:
    """Get the weather in a city, should be a legit city like Paris, London, etc."""
    import random

    weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]
    temperature = random.randint(-10, 35)

    return f"The weather in {city} is {random.choice(weather_conditions)} with temperature {temperature}°C."


@tool
def get_location() -> str:
    """Find user localization."""
    # Simulate location detection failure for demo
    raise Exception("No localization found - please specify your city")


@tool
def escalate_to_user(clarification_question: str) -> str:
    """If you need anything from the user, escalate to him."""
    message = f"{clarification_question}"
    feedback = interrupt(value=message)
    return feedback


def create_weather_agent(
    model: CustomChatModel,
    system_prompt_template: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE,
) -> PydanticReactAgent[WeatherAgentStatePydantic, InputWeatherAgentStatePydantic, OutputWeatherAgentStatePydantic]:
    """
    Create a type-safe weather agent.

    Args:
        model: The language model to use
        system_prompt_template: Custom system prompt template

    Returns:
        Configured weather agent with full type safety
    """
    return PydanticReactAgent(
        name="weather_agent",
        model=model,
        tools=[get_weather, escalate_to_user, get_location],
        state_schema=WeatherAgentStatePydantic,
        input_schema=InputWeatherAgentStatePydantic,
        output_schema=OutputWeatherAgentStatePydantic,
        response_format=Summary,
        system_prompt_template=system_prompt_template,
    )


# Tool for other agents to use this weather agent
@tool
def call_weather_agent(
    state: Annotated[AgentStatePydantic, InjectedState],
    weather_graph=None,  # This would be injected or passed as context
) -> str:
    """
    Call the weather agent to get weather information from user messages.

    This tool invokes a specialized weather agent that can extract location information
    from user messages and provide weather data.

    Args:
        state: The current agent state containing user messages

    Returns:
        Weather summary information
    """
    if weather_graph is None:
        return "Weather agent not available"

    response = weather_graph.invoke(
        InputWeatherAgentStatePydantic(
            messages=[state.messages[0]],
            query="Please find the weather from user messages",
        )
    )
    return str(response.get("summary", "No weather information found"))


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Create the weather agent with full type safety
    model = CustomChatModel(provider="groq")
    weather_agent = create_weather_agent(model)
    weather_graph = weather_agent.get_graph()

    # Test the agent
    test_input = InputWeatherAgentStatePydantic(
        messages=[HumanMessage("What's the weather in Paris?")], query="Weather query for Paris"
    )

    result = weather_graph.invoke(test_input)
    print(f"Weather agent result: {result}")
