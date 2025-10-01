"""Component for displaying artifacts based on type in Streamlit.

Handles different artifact types:
- generic: Simple display with title/description
- followup: Clickable buttons that return the artifact value
- notes: Display with expandable content
"""

from typing import Any, Optional

import streamlit as st
from frontend.types.messages import ArtifactData


def render_artifacts(artifacts: list[ArtifactData], key_prefix: str = "artifacts") -> Optional[str]:
    """Render artifacts based on their type.

    Args:
        artifacts: List of artifact data dictionaries
        key_prefix: Prefix for component keys to avoid conflicts

    Returns:
        The value of the selected artifact if a followup was clicked, None otherwise
    """
    if not artifacts:
        return None

    selected_value = None

    for idx, artifact in enumerate(artifacts):
        artifact_type = artifact.get("type", "generic")
        artifact_data = artifact.get("data", {})
        # Always use key_prefix + idx to ensure uniqueness across messages
        # (same artifact in different messages gets different keys)
        artifact_id = f"{key_prefix}_{idx}"

        # Dispatch to type-specific renderer
        if artifact_type == "followup":
            result = _render_followup_artifact(artifact_data, artifact_id)
            if result:
                selected_value = result

        elif artifact_type == "notes":
            _render_notes_artifact(artifact_data, artifact_id)

        else:  # generic or unknown
            _render_generic_artifact(artifact_data, artifact_id)

    return selected_value


def _render_followup_artifact(artifact: dict[str, Any], key: str) -> Optional[str]:
    """Render a clickable followup artifact.

    Args:
        artifact: Followup artifact data
        key: Unique key for the button

    Returns:
        The artifact value if clicked, None otherwise
    """
    title = artifact.get("title", "Follow-up")
    description = artifact.get("description", "")
    value = artifact.get("value", "")

    # Create clickable button
    if st.button(
        f"💬 {title} : {description}",
        key=f"followup_{key}",
        help=value,
        use_container_width=True,
        icon="⁉️",
    ):
        st.success(icon="✅", body=f"Selected {value}")
        return value

    return None


def _render_generic_artifact(artifact: dict[str, Any], key: str) -> None:
    """Render a generic artifact.

    Args:
        artifact: Generic artifact data
        key: Unique key for components
    """
    title = artifact.get("title", "Artifact")
    description = artifact.get("description", "")

    st.markdown(f"**📋 {title}**")
    if description:
        st.caption(description)


def _render_notes_artifact(artifact: dict[str, Any], key: str) -> None:
    """Render a notes artifact with expandable content.

    Args:
        artifact: Notes artifact data
        key: Unique key for components
    """
    title = artifact.get("title", "Notes")
    description = artifact.get("description", "")
    content = artifact.get("content", "")

    with st.expander(f"📝 {title}", expanded=False):
        if description:
            st.caption(description)
        if content:
            st.markdown(content)

    #
    #
