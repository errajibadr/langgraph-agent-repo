from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class Pagination:
    page: int = 1
    size: int = 20

    @property
    def from_(self) -> int:
        return max(self.page - 1, 0) * self.size


@dataclass
class SearchResult(Generic[T]):
    items: List[T]
    total: int
    aggregations: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None
