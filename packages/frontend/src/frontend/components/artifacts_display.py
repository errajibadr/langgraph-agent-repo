"""Component for displaying clarification artifacts in Streamlit."""

import uuid

import streamlit as st


def render_artifacts(artifacts, key_prefix="artifacts"):
    """Render clarification artifacts as clickable buttons.

    Args:
        artifacts: List of artifacts with fields (title, description)
        key_prefix: Prefix for button keys to avoid conflicts

    Returns:
        The selected artifact index if any button was clicked, None otherwise
    """
    if not artifacts:
        return None

    st.markdown("### 📋 Clarification Options")
    st.markdown("Please select one of the following options:")

    selected_index = None

    # Create columns for better layout (max 2 per row)
    cols_per_row = 2
    rows = [artifacts[i : i + cols_per_row] for i in range(0, len(artifacts), cols_per_row)]

    for row_idx, row_artifacts in enumerate(rows):
        cols = st.columns(len(row_artifacts))

        for col_idx, artifact in enumerate(row_artifacts):
            with cols[col_idx]:
                global_index = row_idx * cols_per_row + col_idx
                # Stable key per message and artifact index to preserve click state across reruns
                button_key = f"{key_prefix}_{global_index}"

                if st.button(
                    f"🎯 {artifact.title}", key=button_key, help=artifact.description, use_container_width=True
                ):
                    selected_index = global_index
                    st.success(f"✅ Selected: {artifact.title}")

                # Show description below button
                st.caption(artifact.description)

    return selected_index


def render_artifacts_compact(artifacts, key_prefix="artifacts_compact"):
    """Render artifacts in a more compact format using selectbox.

    Args:
        artifacts: List of artifacts with fields (title, description)
        key_prefix: Prefix for component keys

    Returns:
        The selected artifact index if selection was made, None otherwise
    """
    if not artifacts:
        return None

    st.markdown("### 📋 Please choose an option:")

    # Create options for selectbox
    display_options = [f"{artifact.title} - {artifact.description}" for artifact in artifacts]

    selected_display = st.selectbox(
        "Available options:",
        options=display_options,
        key=f"{key_prefix}_selectbox_{str(uuid.uuid4())[:8]}",
        help="Select one of the clarification options",
    )

    if selected_display:
        selected_index = display_options.index(selected_display)

        # Confirm button
        if st.button("✅ Confirm Selection", key=f"{key_prefix}_confirm_{str(uuid.uuid4())[:8]}"):
            return selected_index

    return None
