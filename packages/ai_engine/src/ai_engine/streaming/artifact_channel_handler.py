from typing import Any, AsyncGenerator, Optional

from .events import ArtifactEvent, ChannelUpdateEvent, ChannelValueEvent, StreamEvent


class ArtifactChannelHandler:
    """Handle artifact and generic channels for value and update modes."""

    async def handle_values(
        self,
        namespace: str,
        channel_key: str,
        current_value: Any,
        previous_value: Any,
        artifact_type: Optional[str],
        node_name: Optional[str],
        task_id: Optional[str],
        value_delta: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        if artifact_type:
            if not current_value:
                return
            yield ArtifactEvent(
                namespace=namespace,
                channel=channel_key,
                artifact_type=artifact_type,
                artifact_data=current_value,
                is_update=previous_value is not None,
                task_id=task_id,
                node_name=node_name,
            )
        else:
            yield ChannelValueEvent(
                namespace=namespace,
                channel=channel_key,
                value=current_value,
                value_delta=value_delta,
                task_id=task_id,
                node_name=node_name,
            )

    async def handle_update(
        self,
        namespace: str,
        channel_key: str,
        update_value: Any,
        artifact_type: Optional[str],
        node_name: str,
        task_id: Optional[str],
    ) -> AsyncGenerator[StreamEvent, None]:
        if artifact_type:
            if not update_value:
                return
            yield ArtifactEvent(
                namespace=namespace,
                channel=channel_key,
                artifact_type=artifact_type,
                artifact_data=update_value,
                is_update=True,
                task_id=task_id,
                node_name=node_name,
            )
        else:
            yield ChannelUpdateEvent(
                namespace=namespace,
                channel=channel_key,
                node_name=node_name,
                state_update={channel_key: update_value},
                task_id=task_id,
            )
