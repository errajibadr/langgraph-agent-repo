from typing import Any, Dict, List, Optional

from .dtos import Pagination


class QueryBuilder:
    @staticmethod
    def text_query_any_field(text: str) -> Dict[str, Any]:
        return {"simple_query_string": {"query": text, "fields": ["*"]}}

    @staticmethod
    def text_query_in_fields(text: str, fields: List[str]) -> Dict[str, Any]:
        return {"multi_match": {"query": text, "fields": fields}}

    @staticmethod
    def build_filters(
        include_filters: Optional[Dict[str, Any]] = None,
        exclude_filters: Optional[Dict[str, Any]] = None,
        exists_fields: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        filter_clauses: List[Dict[str, Any]] = []
        must_not_clauses: List[Dict[str, Any]] = []

        if include_filters:
            for k, v in include_filters.items():
                if isinstance(v, list):
                    filter_clauses.append({"terms": {k: v}})
                else:
                    filter_clauses.append({"term": {k: v}})

        if exclude_filters:
            for k, v in exclude_filters.items():
                if isinstance(v, list):
                    must_not_clauses.append({"terms": {k: v}})
                else:
                    must_not_clauses.append({"term": {k: v}})

        if exists_fields:
            for f in exists_fields:
                filter_clauses.append({"exists": {"field": f}})

        return {"filter": filter_clauses, "must_not": must_not_clauses}

    @staticmethod
    def base_body(
        query: Dict[str, Any],
        pagination: Optional[Pagination] = None,
        sort: Optional[List[Any]] = None,
        source: Optional[Any] = None,
        aggs: Optional[Dict[str, Any]] = None,
        track_total_hits: Optional[bool] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"query": query}
        if pagination:
            body["from"] = pagination.from_
            body["size"] = pagination.size
        if sort is not None:
            body["sort"] = sort
        if source is not None:
            body["_source"] = source
        if aggs is not None:
            body["aggs"] = aggs
        if track_total_hits is not None:
            body["track_total_hits"] = track_total_hits
        return body
