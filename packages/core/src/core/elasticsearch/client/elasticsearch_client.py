from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch

from ..config.elasticsearch_config import ElasticSearchConfig


class ElasticsearchClient:
    def __init__(self, config: ElasticSearchConfig):
        self.config = config
        self.client: Optional[AsyncElasticsearch] = None

    async def connect(self):
        if self.client is None:
            params = self.config.to_elasticsearch_params()
            self.client = AsyncElasticsearch(**params)

    async def disconnect(self):
        if self.client:
            await self.client.close()
            self.client = None

    async def search(
        self, index: Optional[str] = None, body: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        await self.connect()

        if index is None:
            index = self.config.default_index
        if index is None:
            raise ValueError("No index specified and no default_index in config")

        return await self.client.search(index=index, body=body, **kwargs)

    async def health(self) -> Dict[str, Any]:
        await self.connect()
        return await self.client.cluster.health()

    async def health(self) -> Dict[str, Any]:
        await self.connect()
        return await self.client.cluster.health()
