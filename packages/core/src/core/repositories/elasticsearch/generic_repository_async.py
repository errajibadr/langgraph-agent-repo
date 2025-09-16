from typing import Any, Dict, List, Optional, TypeVar

from core.adapters.elasticsearch.adapters_async import AsyncElasticsearchAdapter
from core.adapters.elasticsearch.dtos import Pagination, SearchResult
from core.adapters.elasticsearch.mapping import HitMapper, build_result
from core.adapters.elasticsearch.query_builder import QueryBuilder
from core.repositories.base import BaseRepository

T = TypeVar("T")


class GenericRepositoryAsync(BaseRepository):
    """Generic async repository for ElasticSearch indices.

    Example:
        ```python
        settings = ElasticsearchSettings()
        adapter = AsyncElasticsearchAdapter(**settings.client_kwargs())
        repo = GenericRepositoryAsync(adapter, index=settings.es_default_index or "datalab-logs-audit-k8s")

        # 1) Raw body
        res = await repo.search_raw_body({"query": {"match_all": {}}, "size": 5})

        # 2) Raw kwargs
        res = await repo.search_raw(query={"term": {"iks_audit.verb": "GET"}}, size=10, track_total_hits=True)

        # 3) Text on all fields
        res = await repo.search_term_all("name", pagination=Pagination(page=1, size=10))

        # 4) Text in specific fields
        res = await repo.search_term_in_fields("action", ["event.action", "iks_audit.requestURI"])

        # 5) Exists filter
        res = await repo.filter_exists(["iks_audit.objectRef.namespace"])
        ```
    """

    def __init__(
        self,
        adapter: AsyncElasticsearchAdapter,
        index: str,
        mapper: Optional[HitMapper[T]] = None,
    ):
        self.adapter = adapter
        self.index = index
        self.mapper = mapper

    async def search_raw_body(
        self,
        body: Dict[str, Any],
        *,
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[T]:
        """Execute a raw ElasticSearch body.

        Args:
            body: Complete ES body dict.
            include_raw: If True, includes raw ES response in result.
        """
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def search_raw(
        self,
        *,
        query: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        from_: Optional[int] = None,
        sort: Optional[List[Any]] = None,
        aggs: Optional[Dict[str, Any]] = None,
        post_filter: Optional[Dict[str, Any]] = None,
        source: Optional[Any] = None,
        track_total_hits: Optional[bool] = None,
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[T]:
        """Build and execute a body from common raw kwargs.

        Typical kwargs mirror ES body parts: query, size, from_, sort, aggs, post_filter, _source.
        """
        body: Dict[str, Any] = {}
        if query is not None:
            body["query"] = query
        if size is not None:
            body["size"] = size
        if from_ is not None:
            body["from"] = from_
        if sort is not None:
            body["sort"] = sort
        if aggs is not None:
            body["aggs"] = aggs
        if post_filter is not None:
            body["post_filter"] = post_filter
        if source is not None:
            body["_source"] = source
        if track_total_hits is not None:
            body["track_total_hits"] = track_total_hits

        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def search_term_all(
        self,
        text: str,
        *,
        include_filters: Optional[Dict[str, Any]] = None,
        exclude_filters: Optional[Dict[str, Any]] = None,
        exists_fields: Optional[List[str]] = None,
        pagination: Pagination = Pagination(),
        sort: Optional[List[Any]] = None,
        source: Optional[Any] = None,
        aggs: Optional[Dict[str, Any]] = None,
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[T]:
        """Search text across all fields using simple_query_string.

        Combine with include_filters/exclude_filters/exists_fields for filtering.
        """
        q_text = QueryBuilder.text_query_any_field(text)
        filters = QueryBuilder.build_filters(include_filters, exclude_filters, exists_fields)
        query = {
            "bool": {
                "must": [q_text],
                "filter": filters["filter"],
                "must_not": filters["must_not"],
            }
        }
        body = QueryBuilder.base_body(query, pagination, sort, source, aggs)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def search_term_in_fields(
        self,
        text: str,
        fields: List[str],
        *,
        include_filters: Optional[Dict[str, Any]] = None,
        exclude_filters: Optional[Dict[str, Any]] = None,
        exists_fields: Optional[List[str]] = None,
        pagination: Pagination = Pagination(),
        sort: Optional[List[Any]] = None,
        source: Optional[Any] = None,
        aggs: Optional[Dict[str, Any]] = None,
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[T]:
        """Search text in a list of fields using multi_match.

        fields: e.g., ["event.action", "iks_audit.requestURI"]
        """
        q_text = QueryBuilder.text_query_in_fields(text, fields)
        filters = QueryBuilder.build_filters(include_filters, exclude_filters, exists_fields)
        query = {
            "bool": {
                "must": [q_text],
                "filter": filters["filter"],
                "must_not": filters["must_not"],
            }
        }
        body = QueryBuilder.base_body(query, pagination, sort, source, aggs)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    async def filter_exists(
        self,
        fields: List[str],
        *,
        pagination: Pagination = Pagination(),
        include_raw: bool = False,
        **kwargs,
    ) -> SearchResult[T]:
        """Filter documents where all provided fields exist."""
        filters = QueryBuilder.build_filters(exists_fields=fields)
        query = {"bool": {"filter": filters["filter"]}}
        body = QueryBuilder.base_body(query, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

    def close(self) -> None:
        pass
