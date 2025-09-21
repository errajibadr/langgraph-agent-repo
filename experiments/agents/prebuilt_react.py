# %%
from turtle import clear

from ai_engine.models.custom_chat_model import create_chat_model
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


# %%
def get_weather(city: str) -> str:
    """Get the weather in a city, should be a legit city like Paris, London, etc."""
    import random

    weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]

    return f"The weather in {city} is {random.choice(weather_conditions)}."


class Summary(BaseModel):
    summary: str


# %%
agent_base = create_react_agent(
    name="agent_prebuilt_react",
    model=create_chat_model(provider="groq"),
    tools=[get_weather],
    prompt="Answer The question the user asks or ask for clarification if needed.",
)


# %%
for chunk in agent_base.stream(
    input={
        "messages": [HumanMessage(content="What's the weather in Paris?")],
        "test": 3,
    },
):
    print(chunk)

# %%
agent_structured = create_react_agent(
    name="agent_prebuilt_react_structured",
    model=create_chat_model(provider="groq"),
    tools=[get_weather],
    prompt="Answer The question the user asks or ask for clarification if needed in type of json",
    response_format={
        "type": "function",
        "name": "summarise",
        "description": "Return a concise summary of the provided text.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The text to summarise"}},
            "required": ["text"],
        },
    },
)

for chunk in agent_structured.stream(
    input={
        "messages": [HumanMessage(content="What's the weather in Paris?")],
        "test": 3,
    },
):
    print(chunk)
# %%

model = create_chat_model(provider="groq")  # , model="moonshotai/kimi-k2-instruct-0905")


result = model.invoke(
    [HumanMessage(content="What's the weather in Paris? reponse in type of json")],
    response_format={
        "type": "json_object",
    },
)

print(result)


# %%
