"""Provider selection and model management UI components."""

import os
from typing import Dict, Tuple

import streamlit as st
from core.types import ProviderType


def render_provider_selector() -> Tuple[ProviderType, str]:
    """Render provider selection dropdown."""
    provider_options = {
        "Custom": ProviderType.CUSTOM,
        "LLMaaS": ProviderType.LLMAAS,
        "LLMaaS Dev": ProviderType.LLMAAS_DEV,
    }

    # Get default provider from environment variable
    env_provider = os.getenv("LLM_PROVIDER", ProviderType.CUSTOM.value)

    # Find the default index based on environment variable
    default_index = 0
    try:
        env_provider_type = ProviderType(env_provider)
        # Find the display name for the environment provider
        for display_name, provider_type in provider_options.items():
            if provider_type == env_provider_type:
                default_index = list(provider_options.keys()).index(display_name)
                break
    except ValueError:
        # If invalid provider in env, default to first option
        default_index = 0

    selected_name = st.selectbox(
        "Select Provider",
        options=list(provider_options.keys()),
        index=default_index,
        help=f"Default provider from .env: {env_provider}",
    )
    selected_provider = provider_options[selected_name]

    return selected_provider, selected_name


def render_model_selection(provider: ProviderType, provider_config: Dict[str, str], env_model_name: str) -> str:
    """Render model selection interface (dropdown or text input)."""
    # Clear models if provider changed
    if st.session_state.models_provider != provider.value:
        st.session_state.fetched_models = []
        st.session_state.models_provider = provider.value

    if st.session_state.fetched_models:
        st.success(f"✅ Found {len(st.session_state.fetched_models)} models! Choose from the dropdown below:")
        model_options = [model.get("id", "Unknown") for model in st.session_state.fetched_models]

        # Pre-select default model: environment variable or provider default
        default_index = 0
        if env_model_name and env_model_name in model_options:
            default_index = model_options.index(env_model_name)
            # Check if this was from env var or provider default
            env_var_name = provider_config.get("model_name_env", "MODEL_NAME")
            if os.getenv(env_var_name):
                st.info(f"🎯 **Using environment variable:** {env_model_name}")
            else:
                st.info(f"🎯 **Using provider default:** {env_model_name}")
        elif env_model_name:
            st.warning(f"⚠️ Default model '{env_model_name}' not found in available models. Using: {model_options[0]}")
        else:
            st.info(f"🎯 **Using first available model:** {model_options[0]}")

        selected_model = st.selectbox(
            f"📋 Select Model ({provider_config.get('model_name_env', 'MODEL_NAME')})",
            options=model_options,
            index=default_index,
            help=f"Models fetched from API. Environment variable: {provider_config.get('model_name_env', 'MODEL_NAME')}",
            key=f"model_select_{provider.value}_{len(st.session_state.fetched_models)}_{hash(str(model_options))}",
        )
        st.info(f"🎯 **Selected:** {selected_model}")
        return selected_model or ""
    else:
        model_input = st.text_input(
            f"✏️ Model Name ({provider_config.get('model_name_env', 'MODEL_NAME')})",
            value=env_model_name or "llama33-70b-instruct",
            help=f"Set via environment variable {provider_config.get('model_name_env', 'MODEL_NAME')} or fetch models first",
        )
        return model_input or "llama33-70b-instruct"
