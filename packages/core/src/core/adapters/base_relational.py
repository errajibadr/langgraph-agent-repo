from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .base import BaseAdapter


class BaseRelationalAdapter(BaseAdapter):
    @abstractmethod
    def execute(self, sql: str, params: Optional[Dict[str, Any] | List] = None, **kwargs) -> Any:
        pass

    def query(self, **kwargs) -> Any:
        return self.execute(**kwargs)
