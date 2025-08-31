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
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel

conn = sqlite3.connect("langgraph.db")


def get_saver():
    conn = sqlite3.connect("langgraph.db", check_same_thread=False)
    return SqliteSaver(conn)


def get_store():
    return InMemoryStore()
