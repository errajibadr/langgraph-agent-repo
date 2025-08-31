import random
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from pydantic import BaseModel


def add_ints(left: int, right: int) -> int:
    return left + right


class GlobalStatePydantic(BaseModel):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    override_int: int = 1
    cumulative: Annotated[int, add_ints] = 1
    dummy_field: str | None = None


def get_weather(city: str) -> str:
    weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]
    return f"The weather in {city} is {random.choice(weather_conditions)}."


def call_llm_node(state: GlobalStatePydantic) -> GlobalStatePydantic:
    from ai_engine.models.custom_chat_model import CustomChatModel

    model = CustomChatModel(model_name="gpt-5-nano").bind_tools([get_weather])
    return GlobalStatePydantic(messages=[model.invoke(state.messages)], override_int=2, cumulative=2)


def post_llm_node_condition(state: GlobalStatePydantic) -> Literal["execute_tools", "__end__"]:
    if not state.messages:
        return "__end__"
    last_message = state.messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"
    return "__end__"


def execute_tools_node(state: GlobalStatePydantic) -> GlobalStatePydantic:
    last_message = state.messages[-1]
    tool_messages = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get("name") == "get_weather":
                weather_response = get_weather(**tool_call.get("args", {}))
                tool_messages.append(ToolMessage(content=weather_response, tool_call_id=tool_call.get("id")))

    return GlobalStatePydantic(messages=tool_messages)


graph = StateGraph(GlobalStatePydantic)

graph.add_node("call_llm_node", call_llm_node)
graph.add_node("execute_tools", execute_tools_node)
graph.add_edge(START, "call_llm_node")
graph.add_conditional_edges(
    "call_llm_node",
    post_llm_node_condition,
    {"__end__": END, "execute_tools": "execute_tools"},
)
graph.add_edge("execute_tools", "call_llm_node")

compiled_graph = graph.compile(checkpointer=MemorySaver(), interrupt_before=["execute_tools"])


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # for chunk in compiled_graph.stream(
    #     GlobalStatePydantic(messages=[HumanMessage("My name is John"), HumanMessage("What is the weather in Paris?")]),
    #     config={"configurable": {"thread_id": "thread-1"}},
    #     stream_mode="values",
    # ):
    #     last_message: AIMessage = chunk["messages"][-1]
    #     last_message.pretty_print()

    for chunk in compiled_graph.stream(
        GlobalStatePydantic(messages=[HumanMessage("What's the weather in Paris?")]),
        config={"configurable": {"thread_id": "thread-1"}},
        stream_mode="values",
    ):
        print(chunk)
        chunk["messages"][-1].pretty_print()
        print(f"chunk[cumulative]: {chunk['cumulative']}, chunk[override_int]: {chunk['override_int']}")

    state = compiled_graph.get_state(config={"configurable": {"thread_id": "thread-1"}})
    print(state.interrupts)
    print(state)
