from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class ArtifactType(str, Enum):
    """Enum for artifact types.
    GENERIC: Generic artifact for any type of artifact
    FOLLOWUP: Follow-up question artifact
    NOTES: Notes artifact
    """

    GENERIC = "generic"
    FOLLOWUP = "followup"
    NOTES = "notes"


class Artifact(BaseModel):
    """Base artifact schema used across agents and frontend.

    Minimal contract to keep LLM output and UI rendering simple.

    Note: `id` and `type` are auto-populated and excluded from LLM JSON schema,
    but are included when serializing for state management.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the artifact",
    )
    type: Literal["generic"] = ArtifactType.GENERIC.value
    title: str = Field(description="Display title shown to the user")
    description: str = Field(description="Brief description of what this option represents")

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_: core_schema.CoreSchema, handler) -> JsonSchemaValue:
        """Customize JSON schema to exclude id and type from LLM generation.

        This hook is called when generating schemas for nested models,
        ensuring id and type are excluded even when used in parent schemas.
        """
        json_schema = handler(core_schema_)
        # Remove id and type from properties
        json_schema.get("properties", {}).pop("id", None)
        json_schema.get("properties", {}).pop("type", None)
        # Remove from required fields
        if "required" in json_schema:
            json_schema["required"] = [f for f in json_schema["required"] if f not in ["id", "type"]]
        return json_schema


class UserChoiceArtifact(Artifact):
    """Optional extension for user-choice artifacts with extra routing data."""

    type: Literal["followup"] = Field(default=ArtifactType.FOLLOWUP.value)
    value: str = Field(description="Value of the follow-up choice")


class NotesArtifact(Artifact):
    """Optional extension for notes-style artifacts, if needed later."""

    type: Literal["notes"] = Field(default=ArtifactType.NOTES.value)
    content: str | None = None


class FollowUpQuestionArtifact(Artifact):
    """Optional extension for follow-up question artifacts, if needed later."""

    type: Literal["followup"] = Field(default=ArtifactType.FOLLOWUP.value)
    value: str = Field(description="Value of the follow-up question")
