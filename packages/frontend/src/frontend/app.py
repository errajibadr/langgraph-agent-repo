import json
import os
from typing import Dict, List

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


def get_models_from_endpoint(base_url: str, api_key: str) -> List[Dict]:
    """Fetch available models from an OpenAI-compatible endpoint."""
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Ensure base_url ends with /v1 if it doesn't already
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

        models_url = f"{base_url}/models"

        response = requests.get(models_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return data["data"]
            else:
                return []
        else:
            st.error(
                f"Failed to fetch models: HTTP {response.status_code}. This may be due to an incorrect API endpoint, network issues, or invalid API credentials. Error details: {response.text[:100]}"
            )
            return []

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error parsing API response: {str(e)}")
        return []


def get_provider_config(provider: ProviderType) -> Dict[str, str]:
    """Get the configuration keys for a given provider."""
    provider_configs = {
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
    return provider_configs.get(provider, {})


def main():
    st.set_page_config(page_title="Multi-Provider LLM Chat", page_icon="🤖", layout="wide")

    st.title("🤖 Multi-Provider LLM Chat Interface")
    st.markdown("Configure and test different LLM providers with ease!")

    # Sidebar for provider configuration
    with st.sidebar:
        st.header("⚙️ Provider Configuration")

        # Provider selection
        provider_options = {
            "Custom": ProviderType.CUSTOM,
            "LLMaaS": ProviderType.LLMAAS,
            "LLMaaS Dev": ProviderType.LLMAAS_DEV,
        }

        selected_provider_name = st.selectbox("Select Provider", options=list(provider_options.keys()), index=0)

        selected_provider = provider_options[selected_provider_name]
        provider_config = get_provider_config(selected_provider)

        st.subheader(f"🔧 {selected_provider_name} Configuration")

        # Get environment variables for the selected provider
        env_api_key = os.getenv(provider_config.get("api_key_env", ""), "")
        env_base_url = os.getenv(provider_config.get("base_url_env", ""), "")
        env_model_name = os.getenv(provider_config.get("model_name_env", ""), "")

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

        # Initialize models in session state if not exists
        if "fetched_models" not in st.session_state:
            st.session_state.fetched_models = []
        if "models_provider" not in st.session_state:
            st.session_state.models_provider = None

        # Clear models if provider changed
        if st.session_state.models_provider != selected_provider.value:
            st.session_state.fetched_models = []
            st.session_state.models_provider = selected_provider.value

        # Fetch models button and clear button in columns
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔍 Fetch Available Models", disabled=not (api_key and base_url)):
                with st.spinner("Fetching models..."):
                    fetched_models = get_models_from_endpoint(base_url, api_key)
                    st.session_state.fetched_models = fetched_models
                    st.session_state.models_provider = selected_provider.value
                    if fetched_models:
                        st.rerun()  # Refresh to show the models immediately

        with col2:
            if st.session_state.fetched_models and st.button("🗑️ Clear"):
                st.session_state.fetched_models = []
                st.rerun()

        # Model selection
        if st.session_state.fetched_models:
            st.success(f"✅ Found {len(st.session_state.fetched_models)} models! Choose from the dropdown below:")
            model_options = [model.get("id", "Unknown") for model in st.session_state.fetched_models]

            # Pre-select the environment model if it exists
            default_index = 0
            if env_model_name and env_model_name in model_options:
                default_index = model_options.index(env_model_name)

            selected_model = st.selectbox(
                f"📋 Select Model ({provider_config.get('model_name_env', 'MODEL_NAME')})",
                options=model_options,
                index=default_index,
                help=f"Models fetched from API. Environment variable: {provider_config.get('model_name_env', 'MODEL_NAME')}",
                key=f"model_select_{selected_provider.value}_{len(st.session_state.fetched_models)}",
            )
            st.info(f"🎯 **Selected:** {selected_model}")
        else:
            st.info("💡 Click 'Fetch Available Models' to see available options, or enter manually:")
            selected_model = st.text_input(
                f"✏️ Model Name ({provider_config.get('model_name_env', 'MODEL_NAME')})",
                value=env_model_name or "llama33-70b-instruct",
                help=f"Set via environment variable {provider_config.get('model_name_env', 'MODEL_NAME')} or fetch models first",
            )

        # Test connection button
        if st.button("🧪 Test Connection"):
            if not all([api_key, base_url, selected_model]):
                st.error("Please fill in all required fields!")
            else:
                try:
                    with st.spinner("Testing connection..."):
                        # Create model instance
                        model = CustomChatModel(
                            provider=selected_provider, api_key=api_key, base_url=base_url, model=selected_model
                        )
                        st.success("✅ Connection successful!")
                        st.info(f"Provider: {selected_provider.value}")
                        st.info(f"Model: {selected_model}")

                        # Store in session state for use in main area
                        st.session_state.current_model = model
                        st.session_state.current_provider = selected_provider_name

                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")

        # Display current configuration
        with st.expander("📋 Current Configuration"):
            st.json(
                {
                    "provider": selected_provider.value,
                    "api_key": f"{api_key[:8]}..." if api_key else "Not set",
                    "base_url": base_url,
                    "model": selected_model,
                }
            )

    # Main chat area
    st.header("💬 Chat Interface")

    if "current_model" in st.session_state:
        st.info(f"🟢 Connected to **{st.session_state.current_provider}** provider")

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to ask?"):
            # Add user message to chat history
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

                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": response_content})

                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

    else:
        st.info("👈 Please configure a provider in the sidebar and test the connection to start chatting!")

        # Show example configurations
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


if __name__ == "__main__":
    main()
