"""Provider settings and configuration models."""

from typing import Optional

from core.types import ProviderType
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseProviderSettings(BaseSettings):
    """Base settings for LLM providers with common configuration."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8")

    # Provider settings
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    base_url: Optional[str] = Field(default=None, description="Base URL for the LLM provider API")
    model_name: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")

    # LLM generation settings
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)")
    top_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling probability (None = disabled)"
    )
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4096, description="Maximum tokens in response")

    @field_validator("api_key", "base_url", "model_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None for proper validation."""
        return None if v == "" else v


class LLMaaSSettings(BaseProviderSettings):
    """Settings for LLMaaS provider."""

    model_config = SettingsConfigDict(
        env_prefix="LLMAAS_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model_name: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")


class LLMaaSDevSettings(BaseProviderSettings):
    """Settings for LLMaaS Development provider."""

    model_config = SettingsConfigDict(
        env_prefix="LLMAAS_DEV_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model_name: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")


class CustomProviderSettings(BaseProviderSettings):
    """Settings for Custom provider."""

    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model_name: Optional[str] = Field(default="gpt-4.1-mini", description="Name of the model to use")


class MultiProviderSettings(BaseSettings):
    """Multi-provider settings with automatic provider selection."""

    provider: ProviderType = Field(default=ProviderType.CUSTOM, description="The LLM provider to use")

    model_config = SettingsConfigDict(
        env_prefix="LLM_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    def get_provider_settings(self) -> BaseProviderSettings:
        """Get the appropriate provider settings based on the selected provider."""
        provider_map = {
            ProviderType.LLMAAS: LLMaaSSettings,
            ProviderType.LLMAAS_DEV: LLMaaSDevSettings,
            ProviderType.CUSTOM: CustomProviderSettings,
        }

        settings_class = provider_map[self.provider]
        return settings_class()
