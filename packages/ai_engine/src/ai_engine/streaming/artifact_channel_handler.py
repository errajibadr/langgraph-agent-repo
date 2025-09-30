from typing import Any, AsyncGenerator, Optional

from core.models.artifacts import Artifact

from .events import ArtifactEvent, ChannelValueEvent, StreamEvent


class ArtifactChannelHandler:
    """Handle artifact and generic channels for value and update modes."""

    async def handle_values(
        self,
        namespace: str,
        channel_key: str,
        artifact_type: str,
        current_value: list[Artifact | Any],
        previous_value: list[Artifact | Any],
        value_delta: Any,
        node_name: Optional[str],
        task_id: Optional[str],
    ) -> AsyncGenerator[StreamEvent, None]:
        if not current_value:
            return

        if artifact_type == "artifact":
            yield ArtifactEvent(
                namespace=namespace,
                channel=channel_key,
                artifact_type=artifact_type,
                artifact_data=current_value,
                is_update=previous_value is not None,
                task_id=task_id,
                node_name=node_name,
            )
        yield ChannelValueEvent(
            namespace=namespace,
            channel=channel_key,
            value=current_value,
            value_delta=value_delta,
            task_id=task_id,
            node_name=node_name,
        )
