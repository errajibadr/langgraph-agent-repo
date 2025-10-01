"""State definitions for the Clarify Agent.

This module contains state classes specific to the clarify agent workflow.
Common states like ClarifyWithUser and UserContext are imported from base.
"""

from typing import Annotated, TypedDict

from core.models import Artifact
from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph import add_messages


class GlobalState(TypedDict):
    """State for the supervisor agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    artifacts: list[Artifact]
