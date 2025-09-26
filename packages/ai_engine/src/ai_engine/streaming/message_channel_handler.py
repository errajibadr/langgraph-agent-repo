import logging
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from .events import MessageReceivedEvent, StreamEvent, ToolCallEvent
from .tool_calls import ToolCallTracker

logger = logging.getLogger(__name__)


class MessageChannelHandler:
    """Handle channels that contain BaseMessage instances (message channels).

    Processes whole messages (no token chunks) and integrates with ToolCallTracker
    to emit ToolCallEvents for AI messages with tool calls and Tool messages with
    tool results.
    """

    def __init__(
        self,
        tool_call_tracker: ToolCallTracker,
        seen_message_ids: set[str],
        parse_namespace_components: Callable,
    ) -> None:
        self.tool_call_tracker = tool_call_tracker
        self.seen_message_ids = seen_message_ids
        self.parse_namespace_components = parse_namespace_components

    async def handle_values(
        self,
        namespace: str,
        channel_key: str,
        current_value: List[BaseMessage],
        previous_value: List[BaseMessage] | None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process channel values that contain messages with deduplication."""

        messages = current_value
        prev_messages = previous_value or []

        # Find new messages (delta)
        new_messages = messages[len(prev_messages) :] if len(messages) > len(prev_messages) else []

        for msg in new_messages:
            msg_id = msg.id
            was_streamed = msg_id is not None and msg_id in self.seen_message_ids
            if not was_streamed:
                self.seen_message_ids.add(msg_id)  # type: ignore we do check that msg_id is not None

            node_name, task_id = self.parse_namespace_components(namespace)

            # Tool call lifecycle integration
            if isinstance(msg, AIMessage):
                ## If we already sent this message ( probably via token by token )
                if msg.content and not was_streamed:
                    # Emit message receipt for UI/telemetry
                    yield MessageReceivedEvent(
                        namespace=namespace,
                        message=msg,
                        was_streamed=was_streamed,
                        has_tool_calls=bool(getattr(msg, "tool_calls", [])),
                        tool_call_ids=[tc.get("id", "") for tc in getattr(msg, "tool_calls", []) if tc.get("id")],
                        source="channel",
                        message_type=msg.type,
                        task_id=task_id,
                    )
                if msg.tool_calls:
                    events = self.tool_call_tracker.process_full_tool_calls(msg, namespace, task_id)
                    for ev in events:
                        yield ev

            if isinstance(msg, ToolMessage):
                events = self.tool_call_tracker.process_tool_call_result(msg, namespace, task_id)
                for ev in events:
                    yield ev
