"""State definitions for the Clarify Agent.

This module contains state classes specific to the clarify agent workflow.
Common states like ClarifyWithUser and UserContext are imported from base.
"""

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph import add_messages

# Import common states from base
from ..base.states import ClarificationArtifact, ClarifyWithUser, UserContext

# Re-export common states for convenience
__all__ = ["ClarifyState", "ClarificationArtifact", "ClarifyWithUser", "UserContext"]


class ClarifyState(TypedDict):
    """State for the clarify agent workflow.

    Tracks the conversation messages, current clarification round,
    maximum allowed rounds, and any clarification artifacts generated.
    """

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    current_round: Annotated[int, add]
    max_rounds: int
    artifacts: Annotated[list[ClarificationArtifact], add]
