from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .base import BaseAdapter


class BaseGraphAdapter(BaseAdapter, ABC):
    @abstractmethod
    def query_graph(self, query: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        pass

    @abstractmethod
    def add_node(self, label: str, properties: Dict[str, Any], **kwargs) -> Any:
        pass

    def query(self, **kwargs) -> Any:
        return self.query_graph(**kwargs)
