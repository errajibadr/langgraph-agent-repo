from typing import List, Optional

from pydantic import BaseModel, Field


class ElasticSearchConfig(BaseModel):
    id: str = Field(..., description="Unique identifier for this config")
    name: Optional[str] = Field(None, description="Descriptive name")

    host: str = Field(..., description="ElasticSearch cluster URL")
    port: Optional[int] = Field(9200, description="Connection port")

    api_key: Optional[str] = Field(None, description="API Key for authentication")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")

    default_index: Optional[str] = Field(None, description="Default index")
    timeout: int = Field(30, description="Timeout in seconds")
    verify_certs: bool = Field(True, description="Verify SSL certificates")

    max_retries: int = Field(3, description="Number of retries")
    retry_on_timeout: bool = Field(True, description="Retry on timeout")

    @property
    def connection_string(self) -> str:
        if self.port and self.port != 9200:
            return f"{self.host}:{self.port}"
        return self.host

    def to_elasticsearch_params(self) -> dict:
        params = {
            "hosts": [self.connection_string],
            "timeout": self.timeout,
            "verify_certs": self.verify_certs,
            "max_retries": self.max_retries,
            "retry_on_timeout": self.retry_on_timeout,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        elif self.username and self.password:
            params["basic_auth"] = (self.username, self.password)

        return params

        return params
