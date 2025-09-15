# ElasticSearch Connector - Architecture Design (UPDATED)

## 📋 Project Context

**Date:** September 15, 2025  
**Component:** ElasticSearch Industrial Connector  
**Package Location:** `packages/core/src/core/elasticsearch/`  
**Purpose:** Flexible ElasticSearch connector for LangGraph agents

## 🎯 Requirements Summary

### Functional Requirements
- **READ-only operations** (no indexation, Filebeat handles that)
- **Single cluster support** (for now, extensible later)
- **Flexible query API** with separated parameters
- **Raw query support** for maximum control
- **Dynamic query generation** for agents

### Technical Requirements
- **Clean configuration** with ElasticSearchConfig class
- **Pydantic Settings** from environment variables
- **Professional naming** (no "Simple" prefixes)
- **Modular architecture** ready for extension
- **Type safety** with Pydantic models

### Target Index (Short Term)
- **Index:** `datalab-logs-audit-k8s`
- **Content:** Kubernetes audit events with business metadata
- **Structure:** Multi-dimensional (iks_audit.*, dws.*, kubernetes.*)
- **Volume:** ~70,000 events per 15 minutes
- **Access:** https://...:9200

## 🏗️ Final Architecture: Simple & Flexible

### Architecture Decision
**Selected Approach:** Simple connector with flexible parameter API

**Rationale:**
- ✅ Start simple, extend later
- ✅ Clean separation of configuration and logic
- ✅ Flexible API for agents (separated parameters)
- ✅ Professional naming conventions
- ✅ Easy to understand and maintain

### Directory Structure
```
packages/core/src/core/elasticsearch/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── elasticsearch_config.py    # ElasticSearchConfig
│   └── settings.py               # ElasticSearchSettings (Pydantic)
├── client/
│   ├── __init__.py
│   └── elasticsearch_client.py   # ElasticsearchClient
└── elasticsearch_connector.py    # ElasticsearchConnector
```

## 🔧 Core Components Design

### 1. ElasticSearch Configuration
```python
# config/elasticsearch_config.py
from pydantic import BaseModel, Field
from typing import Optional

class ElasticSearchConfig(BaseModel):
    """Configuration for ElasticSearch connection"""
    
    # Identification
    id: str = Field(..., description="Unique identifier for this config")
    name: Optional[str] = Field(None, description="Descriptive name")
    
    # Connection
    host: str = Field(..., description="ElasticSearch cluster URL")
    port: Optional[int] = Field(9200, description="Connection port")
    
    # Authentication
    api_key: Optional[str] = Field(None, description="API Key for authentication")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    
    # Configuration
    default_index: Optional[str] = Field(None, description="Default index")
    timeout: int = Field(30, description="Timeout in seconds")
    verify_certs: bool = Field(True, description="Verify SSL certificates")
    
    # Advanced options
    max_retries: int = Field(3, description="Number of retries")
    retry_on_timeout: bool = Field(True, description="Retry on timeout")
    
    @property
    def connection_string(self) -> str:
        """Complete connection URL"""
        if self.port and self.port != 9200:
            return f"{self.host}:{self.port}"
        return self.host
    
    def to_elasticsearch_params(self) -> dict:
        """Convert to ElasticSearch client parameters"""
        params = {
            "hosts": [self.connection_string],
            "timeout": self.timeout,
            "verify_certs": self.verify_certs,
            "max_retries": self.max_retries,
            "retry_on_timeout": self.retry_on_timeout
        }
        
        # Authentication
        if self.api_key:
            params["api_key"] = self.api_key
        elif self.username and self.password:
            params["basic_auth"] = (self.username, self.password)
            
        return params
```

### 2. Pydantic Settings
```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
from .elasticsearch_config import ElasticSearchConfig

class ElasticSearchSettings(BaseSettings):
    """ElasticSearch settings from environment variables"""
    
    # Main configuration (single cluster for now)
    es_id: str = "main"
    es_name: Optional[str] = None
    es_host: str
    es_port: Optional[int] = 9200
    es_api_key: Optional[str] = None
    es_username: Optional[str] = None  
    es_password: Optional[str] = None
    es_default_index: Optional[str] = None
    es_timeout: int = 30
    es_verify_certs: bool = True
    es_max_retries: int = 3
    es_retry_on_timeout: bool = True
    
    class Config:
        env_prefix = "ELASTICSEARCH_"
        env_file = ".env"
    
    def to_elasticsearch_config(self) -> ElasticSearchConfig:
        """Convert settings to ElasticSearchConfig"""
        return ElasticSearchConfig(
            id=self.es_id,
            name=self.es_name or f"ElasticSearch {self.es_id}",
            host=self.es_host,
            port=self.es_port,
            api_key=self.es_api_key,
            username=self.es_username,
            password=self.es_password,
            default_index=self.es_default_index,
            timeout=self.es_timeout,
            verify_certs=self.es_verify_certs,
            max_retries=self.es_max_retries,
            retry_on_timeout=self.es_retry_on_timeout
        )
```

### 3. ElasticSearch Client
```python
# client/elasticsearch_client.py
from elasticsearch import AsyncElasticsearch
from ..config.elasticsearch_config import ElasticSearchConfig
from typing import Dict, Any, Optional

class ElasticsearchClient:
    """Professional ElasticSearch client"""
    
    def __init__(self, config: ElasticSearchConfig):
        self.config = config
        self.client: Optional[AsyncElasticsearch] = None
    
    async def connect(self):
        """Establish connection"""
        if self.client is None:
            params = self.config.to_elasticsearch_params()
            self.client = AsyncElasticsearch(**params)
    
    async def disconnect(self):
        """Close connection"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def search(
        self, 
        index: Optional[str] = None, 
        body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute search with complete body"""
        await self.connect()
        
        if index is None:
            index = self.config.default_index
        if index is None:
            raise ValueError("No index specified and no default_index in config")
        
        return await self.client.search(index=index, body=body, **kwargs)
    
    async def health(self) -> Dict[str, Any]:
        """Check cluster health"""
        await self.connect()
        return await self.client.cluster.health()
```

### 4. Flexible ElasticSearch Connector
```python
# elasticsearch_connector.py
import json
from typing import Dict, Any, List, Optional, Union

class ElasticsearchConnector:
    """ElasticSearch connector with flexible API"""
    
    def __init__(self, config: ElasticSearchConfig):
        self.config = config
        self.client = ElasticsearchClient(config)
    
    async def search(
        self,
        # Query components - SEPARATED PARAMETERS
        query: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        from_: Optional[int] = None,
        sort: Optional[Union[List, Dict, str]] = None,
        aggs: Optional[Dict[str, Any]] = None,
        _source: Optional[Union[List[str], bool, str]] = None,
        
        # Index and options
        index: Optional[str] = None,
        
        # Complete body (alternative)
        body: Optional[Dict[str, Any]] = None,
        
        # Other ElasticSearch parameters
        **kwargs
    ) -> Dict[str, Any]:
        """
        ElasticSearch search with separated parameters
        
        Args:
            query: ElasticSearch query (dict) - ex: {"match": {"field": "value"}}
            size: Number of results to return
            from_: Offset for pagination (from is Python keyword)
            sort: Sort criteria - list, dict or string
            aggs: ElasticSearch aggregations
            _source: Fields to include in results
            index: Index to search
            body: Complete body (ignores other params if provided)
            
        Returns:
            ElasticSearch results
            
        Examples:
            # Simple search
            await connector.search(
                query={"match": {"name": "code-ap"}},
                size=10
            )
            
            # With aggregations
            await connector.search(
                query={"match_all": {}},
                aggs={"by_namespace": {"terms": {"field": "namespace"}}},
                size=0
            )
            
            # With sort and pagination
            await connector.search(
                query={"range": {"@timestamp": {"gte": "now-1h"}}},
                sort=[{"@timestamp": {"order": "desc"}}],
                from_=20,
                size=10
            )
        """
        
        # If body is provided, use it directly
        if body is not None:
            return await self.client.search(index=index, body=body, **kwargs)
        
        # Otherwise, build body from parameters
        request_body = {}
        
        # Query
        if query is not None:
            request_body["query"] = query
        
        # Size
        if size is not None:
            request_body["size"] = size
            
        # Pagination
        if from_ is not None:
            request_body["from"] = from_
        
        # Sort
        if sort is not None:
            request_body["sort"] = sort
            
        # Aggregations
        if aggs is not None:
            request_body["aggs"] = aggs
            
        # Source fields
        if _source is not None:
            request_body["_source"] = _source
        
        # If no query specified, use match_all
        if "query" not in request_body:
            request_body["query"] = {"match_all": {}}
        
        return await self.client.search(index=index, body=request_body, **kwargs)
    
    async def search_raw(
        self, 
        raw_query: Union[str, Dict[str, Any]], 
        index: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search with raw JSON query (for compatibility)
        
        Args:
            raw_query: Complete query in JSON (string or dict)
            index: Index to search
        """
        
        if isinstance(raw_query, str):
            try:
                body = json.loads(raw_query)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON query: {e}")
        else:
            body = raw_query
        
        return await self.search(body=body, index=index, **kwargs)
    
    # Helper methods
    
    async def list_indices(self) -> List[str]:
        """List all indices"""
        await self.client.connect()
        response = await self.client.client.cat.indices(format="json")
        return [idx["index"] for idx in response]
    
    async def get_mapping(self, index: Optional[str] = None) -> Dict[str, Any]:
        """Get index mapping"""
        if index is None:
            index = self.config.default_index
        if index is None:
            raise ValueError("No index specified")
            
        await self.client.connect()
        return await self.client.client.indices.get_mapping(index=index)
    
    async def sample_documents(
        self, 
        size: int = 3, 
        index: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get sample documents"""
        response = await self.search(
            query={"match_all": {}}, 
            size=size, 
            index=index
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cluster health"""
        return await self.client.health()
    
    async def close(self):
        """Close connections"""
        await self.client.disconnect()
```

## 📦 Package Integration

### Update core/pyproject.toml
```toml
[project]
name = "core"
version = "0.1.0"
description = "Core business logic, models, and shared utilities"
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    # ElasticSearch dependencies
    "elasticsearch>=8.0.0",
]
```

## 🛠️ Usage Examples

### Environment Variables (.env)
```bash
# ElasticSearch Configuration
ELASTICSEARCH_ES_HOST=https://your-elasticsearch-cluster.com
ELASTICSEARCH_ES_API_KEY=your-api-key-here
ELASTICSEARCH_ES_DEFAULT_INDEX=datalab-logs-audit-k8s
ELASTICSEARCH_ES_TIMEOUT=30

# Or with username/password
# ELASTICSEARCH_ES_USERNAME=elastic
# ELASTICSEARCH_ES_PASSWORD=your-password
```

### Basic Usage
```python
# Initialization from env vars
from core.elasticsearch.config.settings import ElasticSearchSettings

settings = ElasticSearchSettings()
config = settings.to_elasticsearch_config()
connector = ElasticsearchConnector(config)

# Direct initialization
config = ElasticSearchConfig(
    id="main",
    host="https://elasticsearch.company.com",
    api_key="your-key",
    default_index="datalab-logs-audit-k8s"
)
connector = ElasticsearchConnector(config)

# Flexible search with separated parameters
results = await connector.search(
    query={"match": {"iks_audit.objectRef.name": "code-ap"}},
    size=10,
    sort=[{"@timestamp": {"order": "desc"}}]
)

# Search with aggregations
results = await connector.search(
    query={"range": {"@timestamp": {"gte": "now-1h"}}},
    aggs={
        "by_namespace": {
            "terms": {"field": "kubernetes.namespace"}
        },
        "by_verb": {
            "terms": {"field": "iks_audit.verb"}
        }
    },
    size=0  # No documents, just aggregations
)

# Raw query (for compatibility)
raw_query = """
{
    "query": {"match": {"name": "code-ap"}},
    "size": 5,
    "sort": [{"@timestamp": "desc"}]
}
"""
results = await connector.search_raw(raw_query)

# Helper methods
indices = await connector.list_indices()
health = await connector.health_check()
samples = await connector.sample_documents(size=5)

# Cleanup
await connector.close()
```

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] ElasticSearchConfig with Pydantic validation
- [ ] ElasticSearchSettings from environment variables
- [ ] ElasticsearchClient with connection management
- [ ] Basic ElasticsearchConnector with flexible API

### Phase 2: Testing & Refinement (Week 2)  
- [ ] Unit tests for all components
- [ ] Integration tests with real ElasticSearch
- [ ] Error handling and edge cases
- [ ] Documentation and examples

### Phase 3: LangChain Integration (Week 3)
- [ ] LangChain tool wrapper
- [ ] Agent integration examples
- [ ] Performance optimization
- [ ] Monitoring and logging

### Phase 4: Extensions (Future)
- [ ] Multi-cluster support
- [ ] Repository pattern (if needed)
- [ ] Search strategies (semantic, etc.)
- [ ] Advanced query builders

## ✅ Success Criteria

- [ ] **Clean Configuration**: Easy setup with environment variables
- [ ] **Flexible API**: Agents can use separated parameters or raw queries  
- [ ] **Professional Code**: No "Simple" naming, clean architecture
- [ ] **Type Safety**: Full Pydantic model coverage
- [ ] **Performance**: Handle 70k+ events efficiently
- [ ] **Extensibility**: Easy to add features later

---

**Architecture Status:** ✅ APPROVED - Ready for implementation
**Next Step:** Start with Phase 1 core infrastructure
