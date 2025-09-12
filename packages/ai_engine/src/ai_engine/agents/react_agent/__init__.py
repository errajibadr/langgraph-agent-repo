"""
Generic React Agent with full type safety.

This module provides a type-safe React Agent implementation that works with
different state schemas while preserving type information at both compile-time
and runtime.

Key Features:
- Generic type parameters for StateT, InputT, OutputT
- Runtime type validation
- LangGraph integration
- Clean separation of concerns
- Extensible design

Example Usage:
    ```python
    from ai_engine.agents.react_agent import PydanticReactAgent
    from ai_engine.agents.react_agent.examples.weather_agent import (
        create_weather_agent,
        WeatherAgentStatePydantic,
        InputWeatherAgentStatePydantic,
        OutputWeatherAgentStatePydantic
    )

    # Create a type-safe weather agent
    model = CustomChatModel(provider="groq")
    weather_agent: PydanticReactAgent[
        WeatherAgentStatePydantic,
        InputWeatherAgentStatePydantic,
        OutputWeatherAgentStatePydantic
    ] = create_weather_agent(model)

    # Get the compiled graph
    graph = weather_agent.get_graph()
    ```
"""

from .base import PydanticReactAgent, create_simple_agent
from .types import DEFAULT_SYSTEM_PROMPT_TEMPLATE, InputT, OutputT, StateSchemaType, StateT, ToolType

__all__ = [
    "PydanticReactAgent",
    "create_simple_agent",
    "StateT",
    "InputT",
    "OutputT",
    "ToolType",
    "StateSchemaType",
    "DEFAULT_SYSTEM_PROMPT_TEMPLATE",
]
