from typing import Any, Callable, Dict, List, Optional, TypeVar

from .dtos import SearchResult

T = TypeVar("T")
HitMapper = Callable[[Dict[str, Any]], T]


def default_map_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    src = hit.get("_source", {}) or {}
    out = dict(src)
    out.setdefault("_id", hit.get("_id"))
    return out


def parse_total(resp: Dict[str, Any], fallback_count: int) -> int:
    total_obj = resp.get("hits", {}).get("total", {})
    if isinstance(total_obj, dict) and "value" in total_obj:
        return int(total_obj["value"])
    return fallback_count


def build_result(
    resp: Dict[str, Any],
    mapper: Optional[HitMapper[T]] = None,
    include_raw: bool = False,
) -> SearchResult[T]:
    hits: List[Dict[str, Any]] = resp.get("hits", {}).get("hits", []) or []
    map_fn: HitMapper[Any] = mapper or default_map_hit  # type: ignore
    items = [map_fn(h) for h in hits]
    total = parse_total(resp, fallback_count=len(items))
    aggs = resp.get("aggregations") or resp.get("aggs")
    return SearchResult(items=items, total=total, aggregations=aggs, raw=(resp if include_raw else None))
