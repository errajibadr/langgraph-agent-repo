from abc import abstractmethod
from typing import Any, Dict

from .base import BaseAdapter


class BaseSearchAdapter(BaseAdapter):
    @abstractmethod
    def search(self, index: str, body: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        pass

    def query(self, **kwargs) -> Any:
        return self.search(**kwargs)
