from typing import TypedDict

from pydantic import BaseModel, Field

## Graph Context


class BaseContext(TypedDict):
    """Base context for the agent workflows."""

    user_id: str


## Model Context


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
