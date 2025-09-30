"""Chat utility functions for conversational interface.

This module provides utility functions for:
- Namespace to speaker name mapping
- Speaker avatar selection
- Tool call status formatting
"""

from frontend.types.messages import ToolCallMessage


def get_speaker_for_namespace(namespace: str) -> str:
    """Map namespace to conversational speaker display name.

    Args:
        namespace: The namespace identifier (e.g., "main", "analysis_agent:task_123")

    Returns:
        Human-readable speaker name

    Examples:
        >>> get_speaker_for_namespace("main")
        'AI'
        >>> get_speaker_for_namespace("analysis_agent:task_123")
        'Analysis Agent'
        >>> get_speaker_for_namespace("deep_research_agent")
        'Deep Research Agent'
    """
    if namespace in ["main", "()", "", "messages"]:
        return "AI"

    # Convert namespace to display name (analysis_agent:task_123 → Analysis Agent)
    base_name = namespace.split(":")[0]
    return base_name.replace("_", " ").title()


def get_avatar(speaker: str) -> str:
    """Get emoji avatar for speaker.

    Args:
        speaker: Speaker display name

    Returns:
        Emoji avatar string

    Examples:
        >>> get_avatar("AI")
        '🤖'
        >>> get_avatar("Analysis Agent")
        '📊'
    """
    avatars = {
        "AI": "🤖",
        "Analysis Agent": "📊",
        "Research Agent": "🔍",
        "Report Generator": "📝",
        "Clarify Agent": "❓",
        "Data Processor": "⚙️",
        "Deep Research Agent": "🔬",
        "Aiops Supervisor Agent": "👔",
        "Aiops Deepsearch Agent": "🕵️",
    }
    return avatars.get(speaker, "🤖")


def get_tool_status_display(tool_message: ToolCallMessage) -> str:
    """Convert tool call status to user-friendly display string.

    Args:
        tool_message: Tool call message dict with 'status' and 'name' keys

    Returns:
        Formatted status string with emoji

    Examples:
        >>> get_tool_status_display({"name": "search", "status": "args_started"})
        '🔧 Calling search...'
        >>> get_tool_status_display({"name": "analyze", "status": "result_success"})
        '✅ analyze completed'
    """
    status_map = {
        "args_streaming": f"🔧 Calling {tool_message['name']}...",
        "args_started": f"🔧 Calling {tool_message['name']}...",
        "args_completed": f"🔍 Executing {tool_message['name']}...",
        "args_ready": f"🔍 Executing {tool_message['name']}...",
        "result_success": f"✅ {tool_message['name']} completed",
        "result_error": f"❌ {tool_message['name']} failed",
    }
    return status_map.get(tool_message["status"], f"🔧 {tool_message['name']}")
