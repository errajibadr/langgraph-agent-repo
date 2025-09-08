import operator
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AnyMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class SupervisorState(TypedDict):
    """State for the supervisor agent."""

    supervisor_messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    research_brief: str
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    raw_notes: Annotated[list[str], operator.add]
    notes: Annotated[list[BaseMessage], add_messages]
    finale_report: str
    compressed_research: str
    ## Config params
    research_iterations: int


class SupervisorOutputState(TypedDict):
    """Output state for the supervisor agent."""

    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
class ConductResearch(BaseModel):
    """Tool for delegating a research task to a specialized sub-agent."""

    research_topic: str = Field(
        description="The topic to research. Should be a single topic, and should be described in high detail (at least a paragraph).",
    )


@tool
class ResearchComplete(BaseModel):
    """Tool for indicating that the research process is complete."""

    pass
