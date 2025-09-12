"""Common types and utilities for React Agents."""

from typing import Any, Callable, Dict, List, Optional, Sequence, Type, TypeVar, Union

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from langgraph.prebuilt.chat_agent_executor import AgentState, AgentStatePydantic, StructuredResponseSchema
from pydantic import BaseModel
from typing_extensions import Annotated, TypedDict

# Type variables for generic state schemas with proper bounds
StateT = TypeVar("StateT", bound=Union[AgentState, AgentStatePydantic, TypedDict, BaseModel])
InputT = TypeVar("InputT", bound=Union[TypedDict, BaseModel])
OutputT = TypeVar("OutputT", bound=Union[TypedDict, BaseModel])

# Common type aliases
ToolType = Union[BaseTool, Callable[..., Any]]
StateSchemaType = Type[Union[AgentState, AgentStatePydantic, TypedDict, BaseModel]]

# Default system prompt template
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant.
You have access to tools to help answer questions.
If you don't have the answer for an ambiguous question, you can ask the user for clarification.

When using tools:
- Use the appropriate tool based on the user's question
- Always provide clear explanations of your findings
- If you need more information, ask follow-up questions

User: {user}
Current time: {current_time}
"""
