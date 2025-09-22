"""Streamlit Integration Guide for LangGraph Streaming Parser.

This guide shows how to use the StreamingGraphParser with Streamlit
to create real-time streaming interfaces for your LangGraph agents.
"""

import asyncio
from typing import Any, Dict

import streamlit as st

# Import your streaming components
from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.aiops_supervisor_agent.states import SupervisorContext
from ai_engine.utils.streaming_parser import StreamingGraphParser, ToolCallState, ToolCallStatus
from langchain_core.messages import BaseMessage, HumanMessage

# =============================================================================
# 1. BASIC STREAMLIT INTEGRATION
# =============================================================================


def basic_streamlit_example():
    """Simple example showing basic streaming integration."""
    st.title("🤖 Basic LangGraph Streaming")

    # User input
    user_query = st.text_input("Ask your question:", placeholder="What's the system status?")

    if st.button("Send") and user_query:
        # Create containers for streaming output
        content_container = st.empty()
        tools_container = st.empty()

        # Define callback functions for streaming events
        def on_content_update(content: str):
            """Update the content display in real-time."""
            with content_container.container():
                st.markdown(f"**Assistant:** {content}")

        def on_tool_call_start(idx: int, name: str, call_id: str):
            """Show when a tool call starts."""
            with tools_container.container():
                st.info(f"🔧 Starting tool: {name}")

        def on_tool_call_complete(idx: int, state: ToolCallState):
            """Show when a tool call completes."""
            with tools_container.container():
                st.success(f"✅ Completed: {state.name}")
                if state.parsed_args:
                    with st.expander("Tool Arguments"):
                        st.json(state.parsed_args)

        # Create the streaming parser
        parser = StreamingGraphParser(
            on_content_update=on_content_update,
            on_tool_call_start=on_tool_call_start,
            on_tool_call_complete=on_tool_call_complete,
        )

        # Run the graph (you'd need to adapt this for Streamlit's async handling)
        st.info("💡 In a real app, you'd run the graph streaming here...")


# =============================================================================
# 2. ADVANCED STREAMLIT INTEGRATION WITH STATE MANAGEMENT
# =============================================================================


def advanced_streamlit_example():
    """Advanced example with proper state management and progress tracking."""
    st.title("🚀 Advanced LangGraph Streaming")

    # Initialize session state
    if "streaming_state" not in st.session_state:
        st.session_state.streaming_state = {
            "content": "",
            "active_tools": {},
            "completed_tools": [],
            "is_streaming": False,
        }

    # User interface
    col1, col2 = st.columns([3, 1])

    with col1:
        user_query = st.text_input("Your question:", key="user_input")

    with col2:
        if st.button("Send", disabled=st.session_state.streaming_state["is_streaming"]):
            if user_query:
                run_streaming_agent(user_query)

    # Display streaming content
    display_streaming_content()

    # Display tool progress
    display_tool_progress()


def run_streaming_agent(query: str):
    """Run the agent with streaming (simplified for demo)."""
    st.session_state.streaming_state["is_streaming"] = True

    # In a real implementation, you'd use st.empty() containers
    # and update them as streaming events come in
    st.info(f"🔄 Processing: {query}")

    # Reset state
    st.session_state.streaming_state = {"content": "", "active_tools": {}, "completed_tools": [], "is_streaming": False}


def display_streaming_content():
    """Display the streaming content."""
    if st.session_state.streaming_state["content"]:
        st.markdown("### 💬 Assistant Response")
        st.markdown(st.session_state.streaming_state["content"])


def display_tool_progress():
    """Display tool call progress."""
    if st.session_state.streaming_state["active_tools"] or st.session_state.streaming_state["completed_tools"]:
        st.markdown("### 🔧 Tool Activity")

        # Show active tools
        for tool_idx, tool_info in st.session_state.streaming_state["active_tools"].items():
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown("🔄 **Building**")
                with col2:
                    st.markdown(f"**{tool_info['name']}**")
                    if tool_info.get("preview"):
                        st.code(tool_info["preview"], language="json")

        # Show completed tools
        for tool_info in st.session_state.streaming_state["completed_tools"]:
            with st.expander(f"✅ {tool_info['name']} (Completed)"):
                if tool_info.get("args"):
                    st.json(tool_info["args"])


# =============================================================================
# 3. PRACTICAL STREAMLIT INTEGRATION CLASS
# =============================================================================


class StreamlitAgentInterface:
    """A complete Streamlit interface for LangGraph streaming agents."""

    def __init__(self, agent_name: str = "AI Assistant"):
        self.agent_name = agent_name
        self.setup_session_state()

    def setup_session_state(self):
        """Initialize Streamlit session state."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "streaming_active" not in st.session_state:
            st.session_state.streaming_active = False
        if "current_tool_calls" not in st.session_state:
            st.session_state.current_tool_calls = {}

    def create_streaming_parser(self) -> StreamingGraphParser:
        """Create a parser configured for Streamlit."""
        return StreamingGraphParser(
            on_content_update=self.handle_content_update,
            on_tool_call_start=self.handle_tool_start,
            on_tool_call_update=self.handle_tool_update,
            on_tool_call_complete=self.handle_tool_complete,
            enable_tool_streaming=True,  # You can make this configurable
            enable_content_streaming=True,
        )

    def handle_content_update(self, content: str):
        """Handle streaming content updates."""
        # Update the current message content
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages[-1]["content"] = content
        else:
            st.session_state.messages.append({"role": "assistant", "content": content})

        # Trigger Streamlit rerun to update display
        st.rerun()

    def handle_tool_start(self, idx: int, name: str, call_id: str):
        """Handle tool call start."""
        st.session_state.current_tool_calls[idx] = {
            "name": name,
            "call_id": call_id,
            "status": "building",
            "args_preview": "Building arguments...",
        }
        st.rerun()

    def handle_tool_update(self, idx: int, state: ToolCallState):
        """Handle tool call updates."""
        if idx in st.session_state.current_tool_calls:
            st.session_state.current_tool_calls[idx].update(
                {
                    "status": state.status.value,
                    "args_preview": state.accumulated_args[:100] + "..."
                    if len(state.accumulated_args) > 100
                    else state.accumulated_args,
                }
            )
            st.rerun()

    def handle_tool_complete(self, idx: int, state: ToolCallState):
        """Handle tool call completion."""
        if idx in st.session_state.current_tool_calls:
            st.session_state.current_tool_calls[idx].update(
                {"status": "complete", "args": state.parsed_args, "args_preview": "✅ Complete"}
            )
            st.rerun()

    def render_chat_interface(self):
        """Render the main chat interface."""
        st.title(f"💬 {self.agent_name}")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        # Display active tool calls
        self.render_tool_calls()

        # Chat input
        if prompt := st.chat_input("Type your message..."):
            self.handle_user_input(prompt)

    def render_tool_calls(self):
        """Render active tool calls."""
        if st.session_state.current_tool_calls:
            with st.expander("🔧 Tool Activity", expanded=True):
                for idx, tool_info in st.session_state.current_tool_calls.items():
                    col1, col2, col3 = st.columns([1, 2, 4])

                    with col1:
                        if tool_info["status"] == "building":
                            st.markdown("🔄")
                        elif tool_info["status"] == "complete":
                            st.markdown("✅")
                        else:
                            st.markdown("❌")

                    with col2:
                        st.markdown(f"**{tool_info['name']}**")

                    with col3:
                        if tool_info["status"] == "complete" and "args" in tool_info:
                            st.json(tool_info["args"])
                        else:
                            st.code(tool_info["args_preview"], language="json")

    def handle_user_input(self, prompt: str):
        """Handle user input and start streaming."""
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Clear previous tool calls
        st.session_state.current_tool_calls = {}

        # Start streaming (you'd implement the actual agent call here)
        st.session_state.streaming_active = True

        # Placeholder for actual agent streaming
        st.info("🔄 Agent is processing your request...")

        # In a real implementation, you'd call your agent here:
        # asyncio.run(self.stream_agent_response(prompt))


# =============================================================================
# 4. USAGE EXAMPLES
# =============================================================================


def main():
    """Main function showing different usage patterns."""
    st.sidebar.title("🎛️ Streaming Options")

    mode = st.sidebar.selectbox("Choose interface mode:", ["Basic Example", "Advanced Example", "Complete Interface"])

    if mode == "Basic Example":
        basic_streamlit_example()

    elif mode == "Advanced Example":
        advanced_streamlit_example()

    elif mode == "Complete Interface":
        interface = StreamlitAgentInterface("LangGraph Supervisor")
        interface.render_chat_interface()

    # Configuration options
    st.sidebar.markdown("### ⚙️ Streaming Settings")
    enable_tools = st.sidebar.checkbox("Show tool streaming", value=True)
    enable_content = st.sidebar.checkbox("Show content streaming", value=True)

    if st.sidebar.button("Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# =============================================================================
# 5. INTEGRATION TIPS
# =============================================================================

"""
🎯 INTEGRATION TIPS FOR YOUR STREAMLIT APP:

1. **Session State Management**:
   - Use st.session_state to persist streaming data
   - Clear state between different queries
   - Handle browser refresh gracefully

2. **Container Strategy**:
   - Use st.empty() for dynamic content updates
   - Create separate containers for content and tools
   - Use st.rerun() to trigger UI updates

3. **Async Handling**:
   - Streamlit doesn't handle async well by default
   - Consider using threading or background tasks
   - Use st.spinner() for long-running operations

4. **Performance**:
   - Limit tool call display to prevent UI lag
   - Use st.expander() for detailed tool information
   - Consider pagination for long conversations

5. **Error Handling**:
   - Wrap streaming calls in try/catch
   - Show user-friendly error messages
   - Provide retry mechanisms

6. **User Experience**:
   - Show progress indicators during streaming
   - Disable input while streaming is active
   - Provide clear visual feedback for tool states

EXAMPLE INTEGRATION IN YOUR APP:

```python
# In your main Streamlit app
from ai_engine.utils.streaming_parser import StreamingGraphParser

# Create parser with Streamlit callbacks
parser = StreamingGraphParser(
    on_content_update=lambda content: update_streamlit_content(content),
    on_tool_call_start=lambda idx, name, id: show_tool_start(name),
    on_tool_call_complete=lambda idx, state: show_tool_complete(state),
    enable_tool_streaming=st.session_state.get('show_tools', True)
)

# Use in your graph streaming
async for mode, chunk in graph.astream(...):
    if mode == "messages" and isinstance(chunk[0], BaseMessage):
        parser.process_chunk(chunk[0])
```
"""

if __name__ == "__main__":
    main()
