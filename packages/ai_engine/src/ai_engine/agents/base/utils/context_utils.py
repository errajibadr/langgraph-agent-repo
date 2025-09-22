"""Context utility functions for AI agents."""

from ..states.common_states import UserContext


def get_user_context(user_id: str) -> UserContext:
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
    return UserContext(
        user_id=user_id,
        user_name="John Doe",
        user_teams=["AioPS", "old_team"],
        user_apps=["lgPlatform", "MlEngine"],
        user_environments=["prod", "dev"],
        current_incidents_alerts="No incidents or alerts",
    )
