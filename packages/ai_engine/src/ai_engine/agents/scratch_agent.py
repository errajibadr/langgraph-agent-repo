import random
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from typing_extensions import TypedDict


class GlobalStateSchema(TypedDict):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


def get_weather(city: str) -> str:
    weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]
    return f"The weather in {city} is {random.choice(weather_conditions)}."


def call_llm_node(state: GlobalStateSchema) -> GlobalStateSchema:
    from ai_engine.models.custom_chat_model import CustomChatModel

    model = CustomChatModel(model_name="gpt-5-nano").bind_tools([get_weather])
    return {"messages": [model.invoke(state["messages"])]}


def post_llm_node_condition(state: GlobalStateSchema) -> Literal["execute_tools", "__end__"]:
    last_message = state["messages"][-1]
    print(f"----{type(last_message)}")

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"
    return "__end__"


def execute_tools_node(state: GlobalStateSchema) -> GlobalStateSchema:
    last_message = state["messages"][-1]
    tool_messages = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get("name") == "get_weather":
                weather_response = get_weather(**tool_call.get("args", {}))
                tool_messages.append(ToolMessage(content=weather_response, tool_call_id=tool_call.get("id")))

    return {"messages": tool_messages}


graph = StateGraph(GlobalStateSchema)

graph.add_node("call_llm_node", call_llm_node)
graph.add_node("execute_tools", execute_tools_node)
graph.add_edge(START, "call_llm_node")
graph.add_conditional_edges(
    "call_llm_node",
    post_llm_node_condition,
    {"__end__": END, "execute_tools": "execute_tools"},
)
graph.add_edge("execute_tools", "call_llm_node")

compiled_graph = graph.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print(
        compiled_graph.invoke(
            GlobalStateSchema(
                messages=[HumanMessage("My name is John"), HumanMessage("What is the weather in Paris?")]
            ),
            config={"configurable": {"thread_id": "thread-1"}},
        )
    )

    print(
        compiled_graph.invoke(
            GlobalStateSchema(messages=[HumanMessage("What's my name?")]),
            config={"configurable": {"thread_id": "thread-1"}},
        )
    )
