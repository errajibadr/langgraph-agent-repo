"""Component for displaying clarification artifacts in Streamlit."""

import uuid

import streamlit as st


def render_artifacts(artifacts, key_prefix="artifacts"):
    """Render clarification artifacts as clickable buttons.

    Args:
        artifacts: List of ClarificationArtifact objects
        key_prefix: Prefix for button keys to avoid conflicts

    Returns:
        The selected artifact ID if any button was clicked, None otherwise
    """
    if not artifacts:
        return None

    st.markdown("### 📋 Clarification Options")
    st.markdown("Please select one of the following options:")

    selected_artifact_id = None

    # Create columns for better layout (max 2 per row)
    cols_per_row = 2
    rows = [artifacts[i : i + cols_per_row] for i in range(0, len(artifacts), cols_per_row)]

    for row_idx, row_artifacts in enumerate(rows):
        cols = st.columns(len(row_artifacts))

        for col_idx, artifact in enumerate(row_artifacts):
            with cols[col_idx]:
                # Generate unique key using UUID to prevent duplicates
                button_key = f"{key_prefix}_{artifact.id}_{str(uuid.uuid4())[:8]}"

                if st.button(
                    f"🎯 {artifact.title}", key=button_key, help=artifact.description, use_container_width=True
                ):
                    selected_artifact_id = artifact.id
                    st.success(f"✅ Selected: {artifact.title}")

                # Show description below button
                st.caption(artifact.description)

    return selected_artifact_id


def render_artifacts_compact(artifacts, key_prefix="artifacts_compact"):
    """Render artifacts in a more compact format using selectbox.

    Args:
        artifacts: List of ClarificationArtifact objects
        key_prefix: Prefix for component keys

    Returns:
        The selected artifact ID if selection was made, None otherwise
    """
    if not artifacts:
        return None

    st.markdown("### 📋 Please choose an option:")

    # Create options for selectbox
    artifact_options = {f"{artifact.title} - {artifact.description}": artifact.id for artifact in artifacts}

    selected_display = st.selectbox(
        "Available options:",
        options=list(artifact_options.keys()),
        key=f"{key_prefix}_selectbox_{str(uuid.uuid4())[:8]}",
        help="Select one of the clarification options",
    )

    if selected_display:
        selected_artifact_id = artifact_options[selected_display]

        # Confirm button
        if st.button("✅ Confirm Selection", key=f"{key_prefix}_confirm_{str(uuid.uuid4())[:8]}"):
            return selected_artifact_id

    return None
