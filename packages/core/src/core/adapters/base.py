from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    @abstractmethod
    def query(self, **kwargs) -> Any:
        pass

    @abstractmethod
    def close(self):
        pass
