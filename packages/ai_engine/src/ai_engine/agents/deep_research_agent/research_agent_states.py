"""State Definitions and Pydantic Schemas for Research Scoping.

This defines the state objects and structured schemas used for
the research agent scoping workflow, including researcher state management and output schemas.
"""

from operator import add as list_add
from typing import Annotated

from langgraph.graph.message import AnyMessage, BaseMessage, add_messages

# from langgraph.graph.state import BaseModel
from pydantic import BaseModel, Field


class ResearchAgentInputState(BaseModel):
    """Input state for the research agent."""

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


class ResearchAgentState(BaseModel):
    """State for the research agent.

    - messages: The messages from the user and the response from the agent.
    - research_brief: The research brief.
    - agents_conversation_canal: The conversation between the agents. *shared between agents*
    - raw_notes: The raw notes from the agents. *shared with research agent*
    - notes: The notes from the agents.
    - finale_report: The final report from the agents.
    """

    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    research_brief: str | None = None
    agents_conversation_canal: Annotated[list[BaseMessage], add_messages]
    raw_notes: Annotated[list[BaseMessage], list_add] = Field(default_factory=list)
    notes: Annotated[list[BaseMessage], list_add] = Field(default_factory=list)
    finale_report: str | None = None


class ResearchAgentOutputState(BaseModel):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    final_report: str | None = None


class ClarifyWithUser(BaseModel):
    """State for the clarify with user node."""

    need_clarification: bool = Field(
        default=False, description="Whether you need more clarification from the user to start the research"
    )
    question: str = Field(description="The question to ask the user to clarify the scope of the research")
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )


class ResearchBrief(BaseModel):
    """State for the research brief node."""

    research_brief: str = Field(description="The research brief")
