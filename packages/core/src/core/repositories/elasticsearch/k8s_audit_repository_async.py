from typing import Any, Dict, List, Optional

from core.adapters.elasticsearch.adapters_async import AsyncElasticsearchAdapter
from core.adapters.elasticsearch.dtos import Pagination, SearchResult
from core.adapters.elasticsearch.mapping import HitMapper, build_result
from core.adapters.elasticsearch.query_builder import QueryBuilder
from core.models.k8s_audit import K8sAuditEvent
from core.repositories.base import BaseRepository


def map_hit_to_k8s_audit(hit: Dict[str, Any]) -> K8sAuditEvent:
    src = hit.get("_source", {}) or {}

    # Build a flattened dict compatible with the model's aliases
    doc: Dict[str, Any] = {
        "@timestamp": src.get("@timestamp"),
        "event.action": (src.get("event", {}) or {}).get("action"),
        "event.dataset": (src.get("event", {}) or {}).get("dataset"),
        "iks_audit.auditID": (src.get("iks_audit", {}) or {}).get("auditID"),
        "iks_audit.level": (src.get("iks_audit", {}) or {}).get("level"),
        "iks_audit.requestURI": (src.get("iks_audit", {}) or {}).get("requestURI"),
        "kubernetes.pod.name": ((src.get("kubernetes", {}) or {}).get("pod", {}) or {}).get("name"),
        "kubernetes.node.name": ((src.get("kubernetes", {}) or {}).get("node", {}) or {}).get("name"),
        "kubernetes.container.name": ((src.get("kubernetes", {}) or {}).get("container", {}) or {}).get("name"),
        "iks_audit.results": (src.get("iks_audit", {}) or {}).get("results"),
    }

    # ObjectRef (if present)
    obj_ref = (src.get("iks_audit", {}) or {}).get("objectRef")
    if isinstance(obj_ref, dict):
        doc["objectRef"] = obj_ref

    # DWS enrichment (if present)
    dws = src.get("dws")
    if isinstance(dws, dict):
        doc["dws"] = dws

    return K8sAuditEvent.model_validate(doc)


class K8sAuditRepositoryAsync(BaseRepository):
    """Async repository for Kubernetes audit events.

    Example:
        ```python
        settings = ElasticsearchSettings()
        adapter = AsyncElasticsearchAdapter(**settings.client_kwargs())
        repo = K8sAuditRepositoryAsync(adapter, index=settings.es_default_index or "datalab-logs-audit-k8s")

        # All docs, paginated
        res = await repo.search_all(pagination=Pagination(page=1, size=10))

        # Filter by namespace
        res = await repo.search_by_namespace("external-secrets")

        # Filter by resource type
        res = await repo.search_by_resource("policyreports")

        # Text search
        res = await repo.text_search("kyverno", fields=["event.action", "iks_audit.requestURI"])
        ```
    """

    def __init__(self, adapter: AsyncElasticsearchAdapter, index: str):
        self.adapter = adapter
        self.index = index
        self.mapper: HitMapper[K8sAuditEvent] = map_hit_to_k8s_audit

    async def search_all(
        self,
        pagination: Pagination = Pagination(),
        *,
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[K8sAuditEvent]:
        body = QueryBuilder.base_body({"match_all": {}}, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def search_by_namespace(
        self,
        namespace: str,
        *,
        pagination: Pagination = Pagination(),
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[K8sAuditEvent]:
        filters = QueryBuilder.build_filters(include_filters={"iks_audit.objectRef.namespace": namespace})
        query = {"bool": {"filter": filters["filter"], "must_not": filters["must_not"]}}
        body = QueryBuilder.base_body(query, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def search_by_resource(
        self,
        resource: str,
        *,
        pagination: Pagination = Pagination(),
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[K8sAuditEvent]:
        filters = QueryBuilder.build_filters(include_filters={"iks_audit.objectRef.resource": resource})
        query = {"bool": {"filter": filters["filter"], "must_not": filters["must_not"]}}
        body = QueryBuilder.base_body(query, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def text_search(
        self,
        text: str,
        *,
        fields: Optional[List[str]] = None,
        pagination: Pagination = Pagination(),
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[K8sAuditEvent]:
        if fields:
            q = QueryBuilder.text_query_in_fields(text, fields)
        else:
            q = QueryBuilder.text_query_any_field(text)
        query = {"bool": {"must": [q]}}
        body = QueryBuilder.base_body(query, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    def close(self) -> None:
        pass
