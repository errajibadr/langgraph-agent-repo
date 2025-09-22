"""Graph selector component for choosing which LangGraph agent to use."""

import streamlit as st

from frontend.services.graph_catalog import catalog


def render_graph_selector():
    """Render the graph selection component in the sidebar."""
    st.sidebar.header("🧠 Agent Selection")

    # Get available graphs
    available_graphs = catalog.get_all_graphs()

    if not available_graphs:
        st.sidebar.warning("No graphs available in catalog")
        return

    # Create options for selectbox
    graph_options = {f"{graph.icon} {graph.name}": graph.id for graph in available_graphs}

    # Graph selection
    selected_display = st.sidebar.selectbox(
        "Choose an AI Agent:",
        options=list(graph_options.keys()),
        key="selected_graph_display",
        help="Select which AI agent to use for processing your queries",
    )

    # Get the selected graph ID
    selected_graph_id = graph_options[selected_display]

    # Store in session state
    if st.session_state.get("selected_graph_id") != selected_graph_id:
        st.session_state.selected_graph_id = selected_graph_id
        # Clear existing graph instance to force recreation
        if "current_graph" in st.session_state:
            del st.session_state.current_graph
        st.rerun()

    # Display graph information
    graph_info = catalog.get_graph_by_id(selected_graph_id)
    if graph_info:
        with st.sidebar.expander("ℹ️ Agent Details", expanded=False):
            st.write(f"**Category:** {graph_info.category}")
            st.write(f"**Description:** {graph_info.description}")

    # Initialize the selected graph
    _initialize_selected_graph(selected_graph_id)


def _initialize_selected_graph(graph_id: str):
    """Initialize the selected graph in session state."""
    if "current_graph" not in st.session_state or st.session_state.get("current_graph_id") != graph_id:
        try:
            with st.spinner(f"Initializing {graph_id}..."):
                # Create graph instance
                graph_instance = catalog.create_graph_instance(graph_id)
                graph_info = catalog.get_graph_by_id(graph_id)

                # Store in session state
                st.session_state.current_graph = graph_instance
                st.session_state.current_graph_id = graph_id
                st.session_state.current_graph_info = graph_info

                if graph_info:
                    st.session_state.current_state_schema = graph_info.default_state_schema
                    st.sidebar.success(f"✅ {graph_info.name} ready!")

        except Exception as e:
            st.sidebar.error(f"❌ Failed to initialize {graph_id}: {str(e)}")
            st.sidebar.exception(e)
