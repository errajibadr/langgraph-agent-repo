"""Debug utilities for development and testing."""

import streamlit as st


def show_debug_info():
    """Show debug information about current conversation state."""
    if st.button("🔍 Debug: Show Message State"):
        st.subheader("Chat History")
        if "chat_history" in st.session_state:
            st.json(st.session_state.chat_history)
        else:
            st.info("No chat history")

        st.subheader("Live Chat")
        if "live_chat" in st.session_state:
            st.json(st.session_state.live_chat)
        else:
            st.info("No live chat")


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
            "result": {"content": "Reflection complete - proceeding with analysis"},
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
            "content": "Analyzing the data now... I've found several interesting patterns. Analysis complete! Key findings: correlation coefficient 0.85, 3 main clusters identified.",
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
            "result": {"content": "covariance: 12.5, variance: 8.2, trends: upward"},
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
        {
            "namespace": "main",
            "message_id": "msg_4",
            "role": "ai",
            "content": "Here's your comprehensive analysis based on the detailed processing: The data shows strong correlation (0.85) with 3 distinct clusters and an upward trend. Covariance of 12.5 indicates significant relationships between variables.",
            "timestamp": "2024-01-01T10:00:07",
            "artifacts": [
                {
                    "type": "notes",
                    "id": "main_c8ccc64b-5eae-4697-8cc5-1fbff5a26e78",
                    "data": {
                        "title": "Analysis Report",
                        "description": "Analysis report for the data",
                        "content": (
                            "Investigate the production logs for the lgPlatform application for the current day (2025-10-01). "
                            "The goal is to identify any errors, warnings, or anomalies that may indicate an issue. "
                            "The research should focus on log entries from the primary application logs, system logs, and any relevant monitoring alerts. "
                            "Include timestamps, severity levels, and relevant context. If possible, cross‑reference with deployment events or configuration changes that occurred today. "
                            "The analysis should produce a concise summary of findings and suggested next steps."
                        ),
                    },
                }
            ],
        },
    ]

    # Add test messages to session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.extend(test_messages)
    st.success(f"Added {len(test_messages)} test messages demonstrating the sequential conversation flow!")
    st.rerun()
