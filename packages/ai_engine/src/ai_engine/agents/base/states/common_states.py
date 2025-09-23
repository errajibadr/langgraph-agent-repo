"""Common state definitions and Pydantic schemas for AI agents.

This module contains reusable state classes and schemas that can be shared
across different agents to avoid duplication and ensure consistency.
"""

from core.models import Artifact as BaseArtifact
from pydantic import BaseModel, Field


class ClarificationArtifact(BaseArtifact):
    """Artifact for clarification options that users can select.

    These artifacts provide concrete options that users can click on
    instead of having to type their response.
    """

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
