"""State definitions for the Clarify Agent.

This module contains state classes specific to the clarify agent workflow.
Common states like ClarifyWithUser and UserContext are imported from base.
"""

from operator import add
from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph import add_messages

from ai_engine.agents.base.states.context import BaseContext


class SupervisorState(TypedDict):
    """State for the supervisor agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]  # User Canal
    supervisor_messages: Annotated[list[AnyMessage | BaseMessage], add_messages]  # Internal Canal
    research_brief: Optional[str]  # Research Brief, eventually received from Clarification Agent

    raw_notes: Annotated[list[str], add]  # Raw Notes from the Search Agents results
    notes: Annotated[list[str], add]  # Notes from the Search Agents results
    finale_report: str  # Final Report from the Aggregator Agent
    compressed_research: str  # Compressed Research from the Aggregator Agent
    ## Config params
    research_iteration: int


class SupervisorOutputState(TypedDict):
    """Output state for the supervisor agent."""

    compressed_research: str
    notes: Annotated[list[str], add]
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]


class SupervisorContext(BaseContext):
    """Context for the supervisor agent."""

    supervisor_system_prompt: Optional[str]
