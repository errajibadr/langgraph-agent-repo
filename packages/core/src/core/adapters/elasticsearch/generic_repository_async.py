from typing import Any, Dict, List, Optional, TypeVar

from .adapters_async import AsyncElasticsearchAdapter
from .dtos import Pagination, SearchResult
from .mapping import HitMapper, build_result
from .query_builder import QueryBuilder

T = TypeVar("T")


class GenericRepositoryAsync:
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
        filters = QueryBuilder.build_filters(exists_fields=fields)
        query = {"bool": {"filter": filters["filter"]}}
        body = QueryBuilder.base_body(query, pagination=pagination)
        resp = await self.adapter.search(index=self.index, body=body, **kwargs)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)
        return build_result(resp, mapper=self.mapper, include_raw=include_raw)

