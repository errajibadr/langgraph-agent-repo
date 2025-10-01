"""Context utility functions for AI agents."""

from langgraph.graph.state import RunnableConfig

from ai_engine.agents.base.states.context import UserContext


def get_user_context(user_id: str | None = None) -> UserContext | None:
    """Get user context information by user ID.

    This is a placeholder implementation that returns mock data.
    In a real implementation, this would fetch user data from a database
    or external service.

    Args:
        user_id: The user ID to get context for

    Returns:
        UserContext object with user information
    """
    # TODO: Replace with actual user context retrieval logic
    if user_id is None:
        return None
    return UserContext(
        user_id=user_id,
        user_name="John Doe",
        user_teams=["AioPS", "old_team"],
        user_apps=["lgPlatform", "MlEngine"],
        user_environments=["prod", "dev"],
        current_incidents_alerts="No incidents or alerts",
    )


def is_subgraph(config: RunnableConfig) -> bool:
    """Check if we are currently in a subgraph."""
    return len(config.get("configurable", {}).get("checkpoint_ns", "").split("|")) > 1
