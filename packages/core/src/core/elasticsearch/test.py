import asyncio
from typing import Dict

from core.elasticsearch import ElasticsearchConnector
from core.elasticsearch.config import ElasticSearchSettings


async def main():
    # 1. Charge les settings depuis .env
    settings = ElasticSearchSettings()
    config = settings.to_elasticsearch_config()

    # 2. Crée le connector
    connector = ElasticsearchConnector(config)

    try:
        # 3. Recherche raw (query JSON complète)
        raw_query = {"query": {"match": {"iks_audit.objectRef.name": "code-ap"}}, "size": 5}
        raw_results: Dict = await connector.search_raw(raw_query)
        print("Raw Results (hits):", raw_results["hits"]["total"]["value"])

        # 4. Recherche flexible avec paramètres séparés
        flexible_results: Dict = await connector.search(
            query={"bool": {"must": [{"term": {"iks_audit.verb": "GET"}}]}},
            size=10,
            sort=[{"@timestamp": {"order": "desc"}}],
            aggs={"by_namespace": {"terms": {"field": "kubernetes.namespace"}}},
        )
        print("Flexible Results (hits):", flexible_results["hits"]["total"]["value"])
        print("Aggregations:", flexible_results["aggregations"])

        # 5. Helpers simples
        indices = await connector.list_indices()
        print("Available Indices:", indices)

        mapping = await connector.get_mapping()
        print("Mapping (first field):", list(mapping.values())[0]["mappings"].keys())

        samples = await connector.sample_documents(size=2)
        print("Sample Documents:", samples)

        health = await connector.health_check()
        print("Cluster Health:", health["status"])

    finally:
        # 6. Nettoyage
        await connector.close()


# Run the async main
if __name__ == "__main__":
    asyncio.run(main())
