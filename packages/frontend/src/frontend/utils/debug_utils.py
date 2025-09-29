# Debugging utilities

import streamlit as st


def show_debug_info():
    """Show debug information about current conversation state."""
    if st.button("🔍 Debug: Show Message State"):
        st.subheader("Current Message State")
        st.json(st.session_state.chat_history)

        if "conversational_processor" in st.session_state:
            adapter = st.session_state.conversational_processor.get_adapter()
            summary = adapter.get_conversation_summary()
            st.subheader("Conversation Summary")
            st.json(summary)


def add_test_messages():
    """Add test messages to verify the rendering works correctly."""
    test_messages = [
        {
            "role": "user",
            "content": "Analyze this data and create a comprehensive report",
            "timestamp": "2024-01-01T10:00:00",
        },
        {
            "id": "msg_2",
            "namespace": "main",
            "role": "ai",
            "content": "I'll help you analyze the data and create a comprehensive report for you...",
            "timestamp": "2024-01-01T10:00:01",
        },
        {
            "namespace": "main",
            "message_id": "msg_2",
            "tool_call_id": "call_123",
            "role": "tool_call",
            "name": "think_tool",
            "status": "result_success",
            "args": {"reflection": "The user is asking me to analyze data..."},
            "result": "Reflection complete - proceeding with analysis",
            "timestamp": "2024-01-01T10:00:02",
        },
        {
            "namespace": "main",
            "message_id": "msg_2",
            "tool_call_id": "call_456",
            "role": "tool_call",
            "name": "analysis_agent",
            "status": "args_streaming",
            "args": None,
            "result": None,
            "timestamp": "2024-01-01T10:00:03",
        },
        {
            "id": "msg_3",
            "namespace": "analysis_agent:task_123",
            "role": "ai",
            "content": "Analyzing the data now... I've found several interesting patterns in the data. Analysis complete! Key findings: correlation coefficient 0.85, 3 main clusters identified.",
            "timestamp": "2024-01-01T10:00:04",
        },
        {
            "namespace": "analysis_agent:task_123",
            "message_id": "msg_3",
            "tool_call_id": "call_789",
            "role": "tool_call",
            "name": "data_processor",
            "status": "result_success",
            "args": {"query": "deep analysis"},
            "result": "covariance: 12.5, variance: 8.2, trends: upward",
            "timestamp": "2024-01-01T10:00:05",
        },
        {
            "id": "msg_4",
            "namespace": "main",
            "role": "ai",
            "content": "Here's your comprehensive analysis based on the detailed processing: The data shows strong correlation (0.85) with 3 distinct clusters and an upward trend. Covariance of 12.5 indicates significant relationships between variables.",
            "artifacts": [
                {
                    "type": "AnalysisReport",
                    "data": {"correlation": 0.85, "clusters": 3, "trend": "upward"},
                    "namespace": "main",
                    "timestamp": "2024-01-01T10:00:06",
                }
            ],
            "timestamp": "2024-01-01T10:00:06",
        },
    ]

    # Add test messages to session state
    st.session_state.chat_history.extend(test_messages)
    st.success(f"Added {len(test_messages)} test messages demonstrating the sequential conversation flow!")
    st.rerun()
