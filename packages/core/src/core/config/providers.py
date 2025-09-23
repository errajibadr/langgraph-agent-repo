"""Provider settings and configuration models."""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.types import ProviderType


class BaseProviderSettings(BaseSettings):
    """Base settings for LLM providers with common configuration."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8")

    # Provider settings
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    base_url: Optional[str] = Field(default=None, description="Base URL for the LLM provider API")
    model: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")

    # LLM generation settings
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)")
    top_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling probability (None = disabled)"
    )
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4096, description="Maximum tokens in response")

    @field_validator("api_key", "base_url", "model", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None for proper validation."""
        return None if v == "" else v


class LLMaaSSettings(BaseProviderSettings):
    """Settings for LLMaaS provider."""

    model_config = SettingsConfigDict(
        env_prefix="LLMAAS_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")


class LLMaaSDevSettings(BaseProviderSettings):
    """Settings for LLMaaS Development provider."""

    model_config = SettingsConfigDict(
        env_prefix="LLMAAS_DEV_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model: Optional[str] = Field(default="llama33-70b-instruct", description="Name of the model to use")


class GroqSettings(BaseProviderSettings):
    """Settings for LLMaaS Development provider."""

    model_config = SettingsConfigDict(
        env_prefix="GROQ_", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model: Optional[str] = Field(default="llama-3.3-70b-versatile", description="Name of the model to use")


class CustomProviderSettings(BaseProviderSettings):
    """Settings for Custom provider."""

    model_config = SettingsConfigDict(
        env_prefix="", case_sensitive=False, extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    model: Optional[str] = Field(default="gpt-4.1-mini", description="Name of the model to use")


class ProviderFactory:
    """Pure static factory for creating provider settings."""

    _provider_map = {
        ProviderType.LLMAAS: LLMaaSSettings,
        ProviderType.LLMAAS_DEV: LLMaaSDevSettings,
        ProviderType.CUSTOM: CustomProviderSettings,
        ProviderType.GROQ: GroqSettings,
    }

    @staticmethod
    def get_provider_settings(provider: ProviderType | None = None) -> BaseProviderSettings:
        """Get the appropriate provider settings based on the selected provider."""
        import os

        if provider is None:
            # Read from environment with fallback to CUSTOM
            provider_str = os.getenv("LLM_PROVIDER", ProviderType.CUSTOM.value)
            print(f"Detected Provider: {provider_str}")
            provider = ProviderType(provider_str)

        if provider not in ProviderFactory._provider_map:
            raise ValueError(
                f"Invalid provider: {provider}, valid providers are: {list(ProviderFactory._provider_map.keys())}"
            )
        settings_class = ProviderFactory._provider_map[provider]
        return settings_class()
