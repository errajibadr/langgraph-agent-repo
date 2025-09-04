import random
import sqlite3
from typing import Annotated, Literal

from ai_engine.models.custom_chat_model import CustomChatModel
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

conn = sqlite3.connect("langgraph.db")


def get_saver():
    conn = sqlite3.connect("langgraph.db", check_same_thread=False)
    return SqliteSaver(conn)


def add_ints(left: int, right: int) -> int:
    return left + right


class GlobalStatePydantic(BaseModel):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    override_int: int = 1
    cumulative: Annotated[int, add_ints] = 1
    dummy_field: str | None = None
    summary: str | None = None


def get_weather(city: str) -> str:
    weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]
    return f"The weather in {city} is {random.choice(weather_conditions)}."


model = CustomChatModel(model_name="gpt-5-nano")

# from langchain_google_vertexai import ChatVertexAI
# model = ChatVertexAI(model_name="gemini-2.5-flash", location="europe-west9")


def call_llm_node(state: GlobalStatePydantic) -> GlobalStatePydantic:
    model_with_tools = model.bind_tools([get_weather])
    return GlobalStatePydantic(messages=[model_with_tools.invoke(state.messages)], override_int=2, cumulative=2)


def summarize_messages(state: GlobalStatePydantic) -> str:
    print("len(state.messages)", len(state.messages))
    if len(state.messages) > 10:
        return "summarize"
    return "__end__"


class Summary(BaseModel):
    summary: str


def summarize_messages_node(state: GlobalStatePydantic) -> GlobalStatePydantic:
    return GlobalStatePydantic(
        summary=model.with_structured_output(Summary)
        .invoke(
            [
                SystemMessage(
                    f"You are a helpful assistant that summarizes messages. Summarize the messages and add them to the following summary: {state.summary}"
                )
            ]
            + state.messages[:-2]
        )
        .summary  # type:ignore
        or "",
        messages=[RemoveMessage(id=message.id) for message in state.messages[:-2]],  # type:ignore
    )


def post_llm_node_condition(state: GlobalStatePydantic) -> Literal["execute_tools", "summarize_messages", "__end__"]:
    if not state.messages:
        return "__end__"
    last_message = state.messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"

    if len(state.messages) > 10:
        return "summarize_messages"
    else:
        return "__end__"


def execute_tools_node(state: GlobalStatePydantic) -> GlobalStatePydantic:
    last_message = state.messages[-1]
    tool_messages = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get("name") == "get_weather":
                weather_response = get_weather(**tool_call.get("args", {}))
                print("calling tool id", tool_call.get("id"))
                tool_messages.append(ToolMessage(content=weather_response, tool_call_id=tool_call.get("id")))

    return GlobalStatePydantic(messages=tool_messages)


def human_feedback_node(state: GlobalStatePydantic):
    response = interrupt("Do you have anything to add?")
    print(response)
    pass


graph = StateGraph(GlobalStatePydantic)

graph.add_node("call_llm_node", call_llm_node)
graph.add_node("summarize_messages", summarize_messages_node)
graph.add_node("execute_tools", execute_tools_node)
graph.add_node("human_feedback", human_feedback_node)

graph.add_edge(START, "call_llm_node")
graph.add_conditional_edges(
    "call_llm_node",
    post_llm_node_condition,
    {
        "summarize_messages": "summarize_messages",
        "execute_tools": "execute_tools",
        "__end__": END,
    },
)
graph.add_edge("execute_tools", "human_feedback")
graph.add_edge("human_feedback", "call_llm_node")
graph.add_edge("summarize_messages", END)
# saver = get_saver()
saver = MemorySaver()

compiled_graph = graph.compile(checkpointer=saver)


# async def stream_events(graph: CompiledStateGraph):
#     async for chunk in graph.astream_events(
#         GlobalStatePydantic(messages=[HumanMessage("I'm doing some testing")]),
#         config={"configurable": {"thread_id": "thread_1"}},
#         version="v2",
#     ):
#         print(chunk)


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
        GlobalStatePydantic(messages=[HumanMessage("What is the weather in Paris?")]),
        config={"configurable": {"thread_id": "thread-1"}},
        stream_mode="updates",
    ):
        print(f"chunk keys: {chunk.keys()}")
        # chunk["messages"][-1].pretty_print()
        # print(f"chunk[cumulative]: {chunk['cumulative']}, chunk[override_int]: {chunk['override_int']}")

    print("----------Interrupt----------------")
    if "__interrupt__" in chunk:
        print(chunk)
        feedback = input("Do you have anything to add?") or "continue"
        feedback_message = HumanMessage(feedback)
        compiled_graph.update_state(
            config={"configurable": {"thread_id": "thread-1"}},
            values=GlobalStatePydantic(messages=[feedback_message] if feedback_message else []),
            as_node="human_feedback",
        )

        for chunk in compiled_graph.stream(
            None,
            config={"configurable": {"thread_id": "thread-1"}},
            stream_mode="values",
        ):
            chunk["messages"][-1].pretty_print()
            print(f"chunk[cumulative]: {chunk['cumulative']}, chunk[override_int]: {chunk['override_int']}")
    # import asyncio

    # asyncio.run(stream_events(compiled_graph))

    # print(compiled_graph.get_state(config={"configurable": {"thread_id": "thread-1"}}).values)
