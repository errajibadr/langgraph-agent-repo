from typing import Optional

from pydantic_settings import BaseSettings

from .elasticsearch_config import ElasticSearchConfig


class ElasticSearchSettings(BaseSettings):
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
            retry_on_timeout=self.es_retry_on_timeout,
        )
