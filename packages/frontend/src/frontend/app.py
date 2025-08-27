import json
import os
from typing import Dict, List, Tuple

import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the custom chat model
try:
    from ai_engine.models.custom_chat_model import CustomChatModel, ProviderType
except ImportError:
    st.error("Could not import ai_engine. Make sure it's installed and accessible.")
    st.stop()


# =============================================================================
# CONFIGURATION AND UTILITIES
# =============================================================================


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


def get_env_values(provider_config: Dict[str, str]) -> Tuple[str, str, str]:
    """Get environment variable values for a provider config."""
    api_key = os.getenv(provider_config.get("api_key_env", ""), "")
    base_url = os.getenv(provider_config.get("base_url_env", ""), "")
    model_name = os.getenv(provider_config.get("model_name_env", ""), "")
    return api_key, base_url, model_name


def fetch_models_from_api(base_url: str, api_key: str) -> List[Dict]:
    """Fetch available models from an OpenAI-compatible endpoint."""
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Ensure base_url ends with /v1
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        response = requests.get(f"{base_url}/models", headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            st.error(f"Failed to fetch models: HTTP {response.status_code}")
            return []

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error parsing API response: {str(e)}")
        return []


def init_session_state():
    """Initialize session state variables."""
    if "fetched_models" not in st.session_state:
        st.session_state.fetched_models = []
    if "models_provider" not in st.session_state:
        st.session_state.models_provider = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


# =============================================================================
# UI COMPONENTS
# =============================================================================


def render_provider_selector() -> Tuple[ProviderType, str]:
    """Render provider selection dropdown."""
    provider_options = {
        "Custom": ProviderType.CUSTOM,
        "LLMaaS": ProviderType.LLMAAS,
        "LLMaaS Dev": ProviderType.LLMAAS_DEV,
    }

    selected_name = st.selectbox("Select Provider", options=list(provider_options.keys()), index=0)
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

        # Pre-select environment model if available
        default_index = 0
        if env_model_name and env_model_name in model_options:
            default_index = model_options.index(env_model_name)

        selected_model = st.selectbox(
            f"📋 Select Model ({provider_config.get('model_name_env', 'MODEL_NAME')})",
            options=model_options,
            index=default_index,
            help=f"Models fetched from API. Environment variable: {provider_config.get('model_name_env', 'MODEL_NAME')}",
            key=f"model_select_{provider.value}_{len(st.session_state.fetched_models)}",
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


def render_sidebar() -> Tuple[ProviderType, str, str, str, str]:
    """Render the sidebar with provider configuration."""
    with st.sidebar:
        st.header("⚙️ Provider Configuration")

        # Provider selection
        selected_provider, selected_provider_name = render_provider_selector()
        provider_configs = get_provider_configs()
        provider_config = provider_configs[selected_provider]

        st.subheader(f"🔧 {selected_provider_name} Configuration")

        # Get environment values
        env_api_key, env_base_url, env_model_name = get_env_values(provider_config)

        # Configuration inputs
        api_key = st.text_input(
            f"API Key ({provider_config.get('api_key_env', 'API_KEY')})",
            value=env_api_key,
            type="password",
            help=f"Set via environment variable {provider_config.get('api_key_env', 'API_KEY')}",
        )

        base_url = st.text_input(
            f"Base URL ({provider_config.get('base_url_env', 'BASE_URL')})",
            value=env_base_url or provider_config.get("default_base_url", ""),
            help=f"Set via environment variable {provider_config.get('base_url_env', 'BASE_URL')}",
        )

        # Model fetching controls
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔍 Fetch Available Models", disabled=not (api_key and base_url)):
                with st.spinner("Fetching models..."):
                    fetched_models = fetch_models_from_api(base_url, api_key)
                    st.session_state.fetched_models = fetched_models
                    st.session_state.models_provider = selected_provider.value
                    if fetched_models:
                        st.rerun()

        with col2:
            if st.session_state.fetched_models and st.button("🗑️"):
                st.session_state.fetched_models = []
                st.rerun()

        # Model selection
        selected_model = render_model_selection(selected_provider, provider_config, env_model_name)

        # Test connection
        if st.button("🧪 Test Connection"):
            if not all([api_key, base_url, selected_model]):
                st.error("Please fill in all required fields!")
            else:
                try:
                    with st.spinner("Testing connection..."):
                        model = CustomChatModel(
                            provider=selected_provider, api_key=api_key, base_url=base_url, model=selected_model
                        )
                        st.success("✅ Connection successful!")
                        st.info(f"Provider: {selected_provider.value}")
                        st.info(f"Model: {selected_model}")

                        # Store in session state
                        st.session_state.current_model = model
                        st.session_state.current_provider = selected_provider_name

                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")

        # Current configuration display
        with st.expander("📋 Current Configuration"):
            st.json(
                {
                    "provider": selected_provider.value,
                    "api_key": f"{api_key[:8]}..." if api_key else "Not set",
                    "base_url": base_url,
                    "model": selected_model,
                }
            )

    return selected_provider, selected_provider_name, api_key, base_url, selected_model


def render_chat_interface():
    """Render the main chat interface."""
    st.header("💬 Chat Interface")

    if "current_model" in st.session_state:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to ask?"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate assistant response
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        response = st.session_state.current_model.invoke(prompt)
                        response_content = response.content if hasattr(response, "content") else str(response)
                        st.markdown(response_content)

                        # Add to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response_content})

                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
    else:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")
        render_example_configurations()


def render_example_configurations():
    """Render example configuration instructions."""
    with st.expander("📖 Example Configurations"):
        st.markdown("""
        ### Environment Variables Setup
        
        **For LLMaaS:**
        ```bash
        export LLM_PROVIDER=llmaas
        export LLMAAS_API_KEY=your_api_key_here
        export LLMAAS_BASE_URL=https://api.llmaas.com/v1
        export LLMAAS_MODEL_NAME=llama33-70b-instruct
        ```
        
        **For LLMaaS Dev:**
        ```bash
        export LLM_PROVIDER=llmaas_dev
        export LLMAAS_DEV_API_KEY=your_dev_api_key_here
        export LLMAAS_DEV_BASE_URL=https://dev.api.llmaas.com/v1
        export LLMAAS_DEV_MODEL_NAME=llama33-70b-instruct
        ```
        
        **For Custom Provider:**
        ```bash
        export LLM_PROVIDER=custom
        export API_KEY=your_custom_api_key_here
        export BASE_URL=https://api.openai.com/v1
        export MODEL_NAME=gpt-3.5-turbo
        ```
        """)


# =============================================================================
# MAIN APPLICATION
# =============================================================================


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(page_title="Multi-Provider LLM Chat", page_icon="🤖", layout="wide")

    # Initialize session state
    init_session_state()

    # Header
    st.title("🤖 Multi-Provider LLM Chat Interface")
    st.markdown("Configure and test different LLM providers with ease!")

    # Render components
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()
