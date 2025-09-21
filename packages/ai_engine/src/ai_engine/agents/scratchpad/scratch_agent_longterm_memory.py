import sqlite3
from typing import Annotated, Literal, TypedDict

from ai_engine.models.custom_chat_model import CustomChatModel
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, Field

conn = sqlite3.connect("data/anggraph.db")


def get_saver():
    conn = sqlite3.connect("data/langgraph.db", check_same_thread=False)
    return SqliteSaver(conn)


def get_store(embbed: bool = False):
    config = {}
    if embbed:
        config["index"] = {
            "dims": 1536,
            "embed": lambda x: x,
            "fields": ["text"],
        }
    return InMemoryStore(**config)


class UserProfile(BaseModel):
    name: str
    age: int
    gender: Literal["male", "female"]
    preferences: list[str]
    interests: list[str]


store = get_store()
store.put(
    ("users", "user_id_1"),
    "profile",
    UserProfile(
        name="John",
        age=30,
        gender="male",
        preferences=["morning routines", "being athletic"],
        interests=["reading", "traveling"],
    ).model_dump(),
)
store.put(
    ("users", "user_id_1"),
    "best_scores",
    {"score": 100, "game": "chess"},
)


class MemoryAgentState(BaseModel):
    short_term_summary: str | None = None
    messages: list[AnyMessage | BaseMessage]


model = CustomChatModel(model_name="gpt-5-nano")


def call_llm_node(state: MemoryAgentState) -> MemoryAgentState:
    return MemoryAgentState(
        messages=[model.invoke([SystemMessage(content="Stay super concise in your answers")] + state.messages)]
    )


class ConversationSummary(BaseModel):
    summary: str = Field(description="A brief summary of the conversation")


def short_term_memory_node(state: MemoryAgentState) -> MemoryAgentState:
    if len(state.messages) > 10:
        model_with_output = model.with_structured_output(ConversationSummary)
        return MemoryAgentState(
            short_term_summary=model_with_output.invoke(
                SystemMessage(content="Summarize the conversation") + state.messages[-2]
            ).summary,
            messages=[RemoveMessage(id=message.id) for message in state.messages[:-2]],
        )
    return state


class Context(TypedDict):
    store: InMemoryStore
    user_id: str


def long_term_memory_node(
    state: MemoryAgentState,
    store: BaseStore,
    config: RunnableConfig,
) -> MemoryAgentState:
    user_id = config.get("configurable", {}).get("user_id")

    if user_id:
        print(f"user_id: {user_id}")
        profile = store.get(("users", user_id), "profile")
        print(f"profile: {profile}; type: {type(profile)}")
        user_profile: UserProfile = UserProfile.model_validate(profile.value)
        model_with_output = model.with_structured_output(UserProfile)
        updated_user_profile = model_with_output.invoke(
            input=[
                SystemMessage(
                    content=f"You are a helpful assistant that summarizes messages. Summarize the messages and add them to the following user Profile {user_profile.model_dump_json()}"
                ),
                *state.messages,
            ]
        )
        if user_profile.model_dump_json() != updated_user_profile.model_dump_json():
            print("updating user profile")
            store.put(("users", user_id), "profile", user_profile.model_dump())

    return state


memory_agent_graph = StateGraph(MemoryAgentState, context_schema=Context)
memory_agent_graph.add_node("call_llm_node", call_llm_node)
memory_agent_graph.add_node("long_term_memory_node", long_term_memory_node)


memory_agent_graph.add_edge(START, "call_llm_node")
memory_agent_graph.add_edge("call_llm_node", "long_term_memory_node")
memory_agent_graph.add_edge("long_term_memory_node", END)


graph = memory_agent_graph.compile(checkpointer=MemorySaver(), store=store)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    conversation = [
        HumanMessage(content="Hello, how are you?"),
        AIMessage(content="I'm doing great, thank you!"),
        HumanMessage(content="I really start enjoying football"),
    ]
    graph.invoke(
        MemoryAgentState(messages=conversation),
        config={
            "configurable": {"thread_id": "thread-1", "user_id": "user_id_1"},
        },
        context=Context(store=store, user_id="user_id_form_context"),
    )
