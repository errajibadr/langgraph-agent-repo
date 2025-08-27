"""Environment variable handling utilities."""

import os
from typing import Dict, Tuple

from core.types import ProviderType


def get_provider_configs() -> Dict[ProviderType, Dict[str, str]]:
    """Get configuration mapping for all providers."""
    return {
        ProviderType.LLMAAS: {
            "api_key_env": "LLMAAS_API_KEY",
            "base_url_env": "LLMAAS_BASE_URL",
            "model_name_env": "LLMAAS_MODEL_NAME",
            "default_base_url": "https://api.llmaas.com/v1",
        },
        ProviderType.LLMAAS_DEV: {
            "api_key_env": "LLMAAS_DEV_API_KEY",
            "base_url_env": "LLMAAS_DEV_BASE_URL",
            "model_name_env": "LLMAAS_DEV_MODEL_NAME",
            "default_base_url": "https://dev.api.llmaas.com/v1",
        },
        ProviderType.CUSTOM: {
            "api_key_env": "API_KEY",
            "base_url_env": "BASE_URL",
            "model_name_env": "MODEL_NAME",
            "default_base_url": "https://api.openai.com/v1",
        },
    }


def get_env_values(provider_config: Dict[str, str], provider: ProviderType) -> Tuple[str, str, str, float, float, int]:
    """Get environment variable values for a provider config with fallback to provider defaults."""
    api_key = os.getenv(provider_config.get("api_key_env", ""), "")
    base_url = os.getenv(provider_config.get("base_url_env", ""), "")
    model_name = os.getenv(provider_config.get("model_name_env", ""), "")

    # Use provider default model if no environment variable is set
    if not model_name:
        provider_defaults = {
            ProviderType.LLMAAS: "llama33-70b-instruct",
            ProviderType.LLMAAS_DEV: "llama33-70b-instruct",
            ProviderType.CUSTOM: "gpt-5-mini",
        }
        model_name = provider_defaults.get(provider, "llama33-70b-instruct")

    # LLM settings with defaults (top_p defaults to 0.9 for UI, but None in model settings)
    temperature = float(os.getenv(provider_config.get("temperature_env", "TEMPERATURE"), "0.7"))
    top_p = float(
        os.getenv(provider_config.get("top_p_env", "TOP_P"), "0.9")
    )  # UI default, model will handle None separately
    max_tokens = int(os.getenv(provider_config.get("max_tokens_env", "MAX_TOKENS"), "1000"))

    return api_key, base_url, model_name, temperature, top_p, max_tokens
