"""State definitions for the Clarify Agent.

This module contains state classes specific to the clarify agent workflow.
Common states like ClarifyWithUser and UserContext are imported from base.
"""

from operator import add
from typing import Annotated, Optional, TypedDict

from core.models import UserChoiceArtifact
from core.models.artifacts import NotesArtifact
from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

# Import common states from base
from ai_engine.agents.base.states import UserContext
from ai_engine.agents.base.states.context import BaseContext

# Re-export common states for convenience
__all__ = ["UserContext"]


#### Clarification models

"""Common state definitions and Pydantic schemas for Clarification agent.

This module contains reusable state classes and schemas that can be shared
across different agents to avoid duplication and ensure consistency.
"""


class ClarificationArtifact(UserChoiceArtifact):
    """Artifact for clarification options that users can select.

    These artifacts provide concrete options that users can click on
    instead of having to type their response.
    `title` and `description` are what is displayed to the user,
    `value` is the value that will be used to route the flow.
    """

    value: str = Field(description="Value of the clarification choice")
    pass


class ClarifyWithUser(BaseModel):
    """State for the clarify with user node.

    Used when an agent needs clarification from the user before proceeding
    with a task. This schema provides a standardized way to handle user
    clarification across different agents.
    """

    need_clarification: bool = Field(
        default=False, description="Whether you need more clarification from the user to proceed"
    )
    question: str = Field(description="The question to ask the user to clarify the request")
    verification: str = Field(
        description="Verification message confirming what will be done after clarification",
    )
    artifacts: list[ClarificationArtifact] = Field(
        default_factory=list,
        # max_length=4,
        description="Clarification artifacts - concrete options the user can select (max 4)",
    )


class ResearchBrief(NotesArtifact):
    """Artifact for Research Brief summary of the user's operational query.

    This brief captures the clarified intent and scope of the user's request
    after the clarification process, ready to be passed to the supervisor
    for agent orchestration.
    `title` : Brief title summarizing the operational query.
    `description` User-friendly description of what will be analyzed.
    `content` is The detailed yet concise research brief based on what the user stated he needs to research.
    """

    content: str = Field(
        description="Includes IF specified: specific scope, timeframe, environment, and analysis type."
    )


#### Clarification States


class ClarifyInputState(TypedDict):
    """Simple input state for the clarify agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


class ClarifyState(TypedDict):
    """State for the clarify agent workflow.

    Tracks the conversation messages, current clarification round,
    maximum allowed rounds, and any clarification artifacts generated.
    """

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    artifacts: list[ClarificationArtifact]
    research_brief: Optional[str]
    clarification_iteration: Annotated[int, add]


class ClarifyContext(BaseContext):
    """Context for the clarify agent workflow."""

    clarify_system_prompt: str
