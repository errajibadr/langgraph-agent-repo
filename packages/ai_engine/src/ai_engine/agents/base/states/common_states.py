"""Common state definitions and Pydantic schemas for AI agents.

This module contains reusable state classes and schemas that can be shared
across different agents to avoid duplication and ensure consistency.
"""

from pydantic import BaseModel, Field


class ClarificationArtifact(BaseModel):
    """Artifact for clarification options that users can select.

    These artifacts provide concrete options that users can click on
    instead of having to type their response.
    """

    id: str = Field(description="Unique identifier for the artifact")
    title: str = Field(description="Display title shown to the user")
    description: str = Field(description="Brief description of what this option does")


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
        max_length=4,
        description="Clarification artifacts - concrete options the user can select (max 4)",
    )


class UserContext(BaseModel):
    """User context information for personalized agent responses.

    Contains user-specific information that agents can use to provide
    more relevant and personalized responses.
    """

    user_name: str = Field(description="The name of the user")
    user_id: str = Field(description="The ID of the user")
    user_teams: list[str] = Field(description="The teams the user is a member of")
    user_apps: list[str] = Field(description="The apps the user has access to")
    user_environments: list[str] = Field(description="The environments the user has access to")
    current_incidents_alerts: str = Field(description="The current incidents and alerts for the user's apps")

    def __str__(self) -> str:
        """Return a formatted string representation of the user context."""
        return (
            f"- User: {self.user_name} (ID: {self.user_id})\n"
            f"- Teams: {', '.join(self.user_teams)}\n"
            f"- Managed Apps: {', '.join(self.user_apps)}\n"
            f"- Accessible Environments: {', '.join(self.user_environments)}\n"
            f"- Current Incidents/Alerts: {self.current_incidents_alerts}"
        )
