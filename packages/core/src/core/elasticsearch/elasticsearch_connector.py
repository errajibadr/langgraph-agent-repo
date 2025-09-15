import json
from typing import Any, Dict, List, Optional, Union

from .client.elasticsearch_client import ElasticsearchClient
from .config.elasticsearch_config import ElasticSearchConfig


class ElasticsearchConnector:
    def __init__(self, config: ElasticSearchConfig):
        self.config = config
        self.client = ElasticsearchClient(config)

    async def search(
        self,
        query: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        from_: Optional[int] = None,
        sort: Optional[Union[List, Dict, str]] = None,
        aggs: Optional[Dict[str, Any]] = None,
        _source: Optional[Union[List[str], bool, str]] = None,
        index: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if body is not None:
            return await self.client.search(index=index, body=body, **kwargs)

        request_body = {}

        if query is not None:
            request_body["query"] = query

        if size is not None:
            request_body["size"] = size

        if from_ is not None:
            request_body["from"] = from_

        if sort is not None:
            request_body["sort"] = sort

        if aggs is not None:
            request_body["aggs"] = aggs

        if _source is not None:
            request_body["_source"] = _source

        if "query" not in request_body:
            request_body["query"] = {"match_all": {}}

        return await self.client.search(index=index, body=request_body, **kwargs)

    async def search_raw(
        self, raw_query: Union[str, Dict[str, Any]], index: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        if isinstance(raw_query, str):
            try:
                body = json.loads(raw_query)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON query: {e}")
        else:
            body = raw_query

        return await self.search(body=body, index=index, **kwargs)

    async def list_indices(self) -> List[str]:
        await self.client.connect()
        response = await self.client.client.cat.indices(format="json")
        return [idx["index"] for idx in response]

    async def get_mapping(self, index: Optional[str] = None) -> Dict[str, Any]:
        if index is None:
            index = self.config.default_index
        if index is None:
            raise ValueError("No index specified")

        await self.client.connect()
        return await self.client.client.indices.get_mapping(index=index)

    async def sample_documents(self, size: int = 3, index: Optional[str] = None) -> List[Dict[str, Any]]:
        response = await self.search(query={"match_all": {}}, size=size, index=index)
        return [hit["_source"] for hit in response["hits"]["hits"]]

    async def health_check(self) -> Dict[str, Any]:
        return await self.client.health()

    async def close(self):
        await self.client.disconnect()

    async def close(self):
        await self.client.disconnect()
