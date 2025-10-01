"""State Definitions and Pydantic Schemas for Research Scoping.

This defines the state objects and structured schemas used for
the research agent scoping workflow, including researcher state management and output schemas.
"""

import operator
from operator import add as list_add
from typing import Annotated, Sequence, TypedDict

from ai_engine.agents.clarify_agent.states import ClarificationArtifact
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from pydantic import BaseModel, Field


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
    supervisor_messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    raw_notes: Annotated[list[str], list_add] = Field(default_factory=list)
    notes: Annotated[list[str], list_add] = Field(default_factory=list)
    finale_report: str | None = None


class ResearchAgentOutputState(BaseModel):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    final_report: str | None = None


# ===== STATE DEFINITIONS =====
class ResearcherState(TypedDict):
    """
    State for the research agent containing message history and research metadata.

    This state tracks the researcher's conversation, iteration count for limiting
    tool calls, the research topic being investigated, compressed findings,
    and raw research notes for detailed analysis.
    """

    researcher_messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    tool_call_iterations: int
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]


class ResearcherOutputState(TypedDict):
    """
    Output state for the research agent containing final research results.

    This represents the final output of the research process with compressed
    research findings and all raw notes from the research process.
    """

    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]


# ===== STRUCTURED OUTPUT SCHEMAS =====


class ResearchBrief(BaseModel):
    """State for the research brief node."""

    research_brief: str = Field(description="The research brief")


class Summary(BaseModel):
    """Schema for webpage content summarization."""

    summary: str = Field(description="Concise summary of the webpage content")
    key_excerpts: str = Field(description="Important quotes and excerpts from the content")
