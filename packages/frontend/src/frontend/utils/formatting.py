"""Formatting utilities for the frontend."""

import re


def beautify_tool_name(tool_name: str) -> str:
    """Convert tool name to beautiful title case.

    Examples:
        call_inspector_agent -> Call Inspector Agent
        callInspectorAgent -> Call Inspector Agent
        think_tool -> Think Tool
        executeQuery -> Execute Query

    Args:
        tool_name: The original tool name (snake_case or camelCase)

    Returns:
        Beautified tool name in Title Case
    """
    # Handle snake_case: call_inspector_agent -> Call Inspector Agent
    if "_" in tool_name:
        words = tool_name.split("_")
        return " ".join(word.capitalize() for word in words)

    # Handle camelCase: callInspectorAgent -> Call Inspector Agent
    # Insert space before uppercase letters (except the first one)
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", tool_name)
    return spaced.title()
