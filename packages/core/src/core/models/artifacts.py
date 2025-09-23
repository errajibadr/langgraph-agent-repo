from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Base artifact schema used across agents and frontend.

    Minimal contract to keep LLM output and UI rendering simple.
    """

    title: str = Field(description="Display title shown to the user")
    description: str = Field(description="Brief description of what this option represents")


class UserChoiceArtifact(Artifact):
    """Optional extension for user-choice artifacts with extra routing data."""

    pass


class NotesArtifact(Artifact):
    """Optional extension for notes-style artifacts, if needed later."""

    content: str | None = None


class FollowUpQuestionArtifact(Artifact):
    """Optional extension for follow-up question artifacts, if needed later."""

    question: str | None = None
    suggestions: list[str] | None = None
