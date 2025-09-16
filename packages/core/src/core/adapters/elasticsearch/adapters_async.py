from typing import Any, Dict

from elasticsearch import AsyncElasticsearch

from core.adapters.base_search import BaseSearchAdapter


class AsyncElasticsearchAdapter(BaseSearchAdapter):
    def __init__(self, **client_kwargs):
        self.client = AsyncElasticsearch(**client_kwargs)

    async def search(self, index: str, body: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        try:
            response = await self.client.search(index=index, body=body, **kwargs)
            return response.body
        except Exception as e:
            raise RuntimeError(f"Elasticsearch search failed: {str(e)}") from e

    async def close(self):
        try:
            await self.client.close()
        except Exception as e:
            raise RuntimeError(f"Failed to close Elasticsearch client: {str(e)}") from e
