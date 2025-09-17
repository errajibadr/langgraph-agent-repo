from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ElasticsearchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ELASTICSEARCH_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    es_host: str
    es_id: str
    es_api_key: str

    es_default_index: Optional[str] = None
    es_verify_certs: bool = True
    es_request_timeout: int = 30
    es_max_retries: int = 3
    es_retry_on_timeout: bool = True

    es_ca_certs: Optional[str] = None
    es_username: Optional[str] = None
    es_password: Optional[str] = None
    es_headers: Optional[Dict[str, str]] = None

    es_extra: Dict[str, Any] = Field(default_factory=dict)

    def client_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "hosts": [self.es_host],
            "api_key": (self.es_id, self.es_api_key),
            "verify_certs": self.es_verify_certs,
            "request_timeout": self.es_request_timeout,
            "max_retries": self.es_max_retries,
            "retry_on_timeout": self.es_retry_on_timeout,
        }

        if self.es_ca_certs:
            kwargs["ca_certs"] = self.es_ca_certs

        # Only set basic_auth if no api_key usage is desired (kept for flexibility)
        if self.es_username and self.es_password and not (self.es_id and self.es_api_key):
            kwargs["basic_auth"] = (self.es_username, self.es_password)

        if self.es_headers:
            kwargs["headers"] = self.es_headers

        if self.es_extra:
            kwargs.update(self.es_extra)

        return kwargs
