"""Component for displaying artifacts based on type in Streamlit.

Handles different artifact types:
- generic: Simple display with title/description
- followup: Clickable buttons that return the artifact value
- notes: Display with expandable content
"""

from typing import Any, Callable, Optional

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
        artifact_id = artifact_data.get("id", f"{key_prefix}_{idx}")

        # Dispatch to type-specific renderer
        if artifact_type == "followup":
            result = _render_followup_artifact(artifact_data, artifact_id)
            if result:
                selected_value = result

        elif artifact_type == "notes":
            _render_notes_artifact(artifact_data, f"{key_prefix}_{idx}")

        else:  # generic or unknown
            _render_generic_artifact(artifact_data, f"{key_prefix}_{idx}")

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
        f"💬 {title}",
        key=f"followup_{key}",
        help=description,
        use_container_width=True,
    ):
        return value

    # Show description below
    if description:
        st.caption(description)

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


def render_followup_options(
    artifacts: list[dict[str, Any]], key_prefix: str = "followup", on_select: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Render followup artifacts as a set of clickable options.

    Specialized renderer for clarification scenarios where we want
    to present multiple followup options clearly.

    Args:
        artifacts: List of followup artifacts
        key_prefix: Prefix for button keys
        on_select: Optional callback when an option is selected

    Returns:
        The selected artifact value if clicked, None otherwise
    """
    if not artifacts:
        return None

    st.markdown("### 💬 Please choose one:")

    selected_value = None

    # Create columns for better layout (max 2 per row)
    cols_per_row = 2
    rows = [artifacts[i : i + cols_per_row] for i in range(0, len(artifacts), cols_per_row)]

    for row_idx, row_artifacts in enumerate(rows):
        cols = st.columns(len(row_artifacts))

        for col_idx, artifact in enumerate(row_artifacts):
            with cols[col_idx]:
                global_index = row_idx * cols_per_row + col_idx
                button_key = f"{key_prefix}_{global_index}"

                title = artifact.get("title", "Option")
                description = artifact.get("description", "")
                value = artifact.get("value", "")

                if st.button(f"🎯 {title}", key=button_key, help=description, use_container_width=True):
                    selected_value = value
                    st.success(f"✅ Selected: {title}")
                    if on_select:
                        on_select(value)

                # Show description below button
                if description:
                    st.caption(description)

    return selected_value
    #
    #
    #
    #
    #
    #
    #
    #
    #
