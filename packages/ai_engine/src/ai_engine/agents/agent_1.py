from typing import Annotated

from ai_engine.utils.tools import get_weather
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing_extensions import TypedDict

load_dotenv()

llm = ChatOpenAI(model="gpt-5-nano", reasoning_effort="minimal", verbosity="low")

agent = create_react_agent(
    name="helper_agent",
    model=llm,
    tools=[get_weather],
    # interrupt_before=["tools"],
    # A static prompt that never changes
    prompt="Just answer questions about the weather.",
)


class StateSchema(TypedDict):
    messages: Annotated[list, add_messages]


class WeatherResponse(BaseModel):
    weather: str
    temperature: float | None = None


def summarizer_agent(state: StateSchema) -> dict:
    response: WeatherResponse = llm.with_structured_output(WeatherResponse).invoke(state["messages"][-1].content)  # type: ignore
    return {
        "messages": [
            {
                "role": "assistant",
                "content": f"The weather in Tokyo is {response.weather} and the temperature is {response.temperature}.",
            }
        ]
    }


graph = StateGraph(state_schema=StateSchema)
graph.add_node("helper_agent", agent)
graph.add_node("summarizer_agent", summarizer_agent)

graph.add_edge(START, "helper_agent")
graph.add_edge("helper_agent", "summarizer_agent")
graph.add_edge("summarizer_agent", END)

compiled_graph = graph.compile()


if __name__ == "__main__":
    # response = agent.stream({"messages": [{"role": "user", "content": "What is the weather in Tokyo?"}]})
    # for chunk in response:
    #     print("--------------------------------")
    #     print(chunk)
    #     print("--------------------------------")
    # print(response["messages"][-1])
    for stream_mode, chunk in compiled_graph.stream(
        {"messages": [{"role": "user", "content": "What is the weather in Tokyo?"}]}, stream_mode=["messages", "custom"]
    ):
        print("-----------chunk-------------")
        print(chunk)
        print("-----------metadata------------")
        print(stream_mode)
        print("--------------------------------")
    # print(
    #     compiled_graph.invoke({"messages": [{"role": "user", "content": "What is the weather in Tokyo?"}]})["messages"]
    # )
