from enum import Enum
from typing import Any, Dict, Optional, Union

from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    LLMAAS = "llmaas"
    LLMAAS_DEV = "llmaas_dev"
    CUSTOM = "custom"


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

    model_name: Optional[str] = Field(default="gpt-5-mini", description="Name of the model to use")


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


class CustomChatModel(ChatOpenAI):
    """
    Multi-provider ChatOpenAI model that supports multiple LLM providers.

    Supported providers:
    - LLMaaS (production): Set LLM_PROVIDER=llmaas, configure with LLMAAS_* env vars
    - LLMaaS Dev (development): Set LLM_PROVIDER=llmaas_dev, configure with LLMAAS_DEV_* env vars
    - Custom: Set LLM_PROVIDER=custom, configure with {NO_PREFIX}* env vars

    Environment variables:
    - LLM_PROVIDER: Provider type (llmaas, llmaas_dev, custom)
    - {PREFIX}_API_KEY: API key for the provider
    - {PREFIX}_BASE_URL: Base URL for the provider API
    - {PREFIX}_MODEL_NAME: Model name to use

    Examples:
        # Using environment variables (recommended)
        export LLM_PROVIDER=llmaas
        export LLMAAS_API_KEY=your_api_key
        export LLMAAS_BASE_URL=https://api.llmaas.com
        export LLMAAS_MODEL_NAME=llama33-70b-instruct
        model = CustomChatModel()

        # Using constructor arguments
        model = CustomChatModel(
            provider="custom",
            api_key="your_key",
            base_url="https://api.example.com",
            model="gpt-3.5-turbo"
        )

        # Using provider-specific constructor
        model = CustomChatModel(provider="llmaas_dev")
    """

    def __init__(self, provider: Union[str, ProviderType] = ProviderType.CUSTOM, *args, **kwargs):
        if provider is not None and (isinstance(provider, str)):
            provider = ProviderType(provider.lower())

        # Load multi-provider settings
        multi_settings = MultiProviderSettings(provider=provider)

        # Get provider-specific settings
        provider_settings = multi_settings.get_provider_settings()

        # Prepare configuration dictionary
        config = {}

        # Use provider settings as defaults
        if provider_settings.api_key is not None:
            config["api_key"] = provider_settings.api_key
        if provider_settings.base_url is not None:
            config["base_url"] = provider_settings.base_url
        if provider_settings.model_name is not None:
            config["model"] = provider_settings.model_name  # ChatOpenAI uses 'model', not 'model_name'

        # Add LLM generation settings
        if provider_settings.temperature is not None:
            config["temperature"] = provider_settings.temperature
        if provider_settings.top_p is not None:
            config["top_p"] = provider_settings.top_p
        if provider_settings.max_tokens is not None:
            config["max_tokens"] = provider_settings.max_tokens

        # Override with any provided kwargs (filter None values for optional params)
        for key, value in kwargs.items():
            if key == "top_p" and value is None:
                # Skip None top_p values to avoid passing None to ChatOpenAI
                config.pop("top_p", None)
            else:
                config[key] = value

        # Validate required parameters
        self._validate_required_config(config, multi_settings.provider)

        print(
            f"CustomChatModel initialized for provider '{multi_settings.provider.value}' with config: {self._safe_config_for_logging(config)}"
        )
        super().__init__(*args, **config)

    def _validate_required_config(self, config: Dict[str, Any], provider: ProviderType) -> None:
        """Validate that all required configuration is present."""
        missing_fields = []

        provider_prefix = {
            ProviderType.LLMAAS: "LLMAAS_",
            ProviderType.LLMAAS_DEV: "LLMAAS_DEV_",
            ProviderType.CUSTOM: "",
        }[provider]

        if not config.get("api_key"):
            missing_fields.append(f"api_key ({provider_prefix}API_KEY)")
        if not config.get("base_url"):
            missing_fields.append(f"base_url ({provider_prefix}BASE_URL)")
        if not config.get("model"):
            missing_fields.append(f"model ({provider_prefix}MODEL_NAME)")

        if missing_fields:
            raise ValueError(
                f"Missing required configuration for provider '{provider.value}': {', '.join(missing_fields)}. "
                f"Please provide these either as constructor arguments or environment variables."
            )

    def _safe_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Return a safe version of config for logging (with masked sensitive data)."""
        safe_config = config.copy()

        # Mask sensitive API key
        if "api_key" in safe_config and safe_config["api_key"]:
            safe_config["api_key"] = safe_config["api_key"][:8] + "..." if len(safe_config["api_key"]) > 8 else "***"

        # Keep only relevant fields for logging
        relevant_fields = ["api_key", "base_url", "model", "temperature", "top_p", "max_tokens"]
        safe_config = {k: v for k, v in safe_config.items() if k in relevant_fields}

        return safe_config


# Factory function for easier provider creation
def create_chat_model(provider: Union[str, ProviderType], **kwargs) -> CustomChatModel:
    """
    Factory function to create a CustomChatModel with a specific provider.

    Args:
        provider: Provider type ('llmaas', 'llmaas_dev', 'custom')
        **kwargs: Additional configuration to override environment variables

    Returns:
        CustomChatModel instance configured for the specified provider

    Examples:
        # Create LLMaaS model
        model = create_chat_model("llmaas")

        # Create custom model with overrides
        model = create_chat_model("custom", api_key="override_key")
    """
    return CustomChatModel(provider=provider, **kwargs)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    CustomChatModel()
