import json
import os
from typing import Dict, List, Optional, Tuple

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
    if "current_model_name" not in st.session_state:
        st.session_state.current_model_name = None
    if "last_config" not in st.session_state:
        st.session_state.last_config = {}


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


def render_llm_configuration(
    temperature: float, top_p: float, max_tokens: int, has_top_p_env: bool = False
) -> Tuple[float, Optional[float], int]:
    """Render LLM configuration controls."""
    with st.expander("🎛️ LLM Configuration", expanded=False):
        st.markdown("**Generation Settings**")

        col1, col2 = st.columns(2)

        with col1:
            temperature_input = st.slider(
                "🌡️ Temperature",
                min_value=0.0,
                max_value=2.0,
                value=temperature,
                step=0.1,
                help="Controls randomness. Higher values make output more creative but less focused.",
            )

            max_tokens_input = st.slider(
                "📏 Max Tokens",
                min_value=50,
                max_value=4096,
                value=max_tokens,
                step=50,
                help="Maximum number of tokens to generate in the response.",
            )

        with col2:
            # Top P with optional checkbox - enable if environment variable is set
            checkbox_default = has_top_p_env  # Enable if env var is set
            use_top_p = st.checkbox(
                "Enable Top P",
                value=checkbox_default,
                help="Some models don't support top_p parameter. Enable only if needed.",
            )

            if has_top_p_env and use_top_p:
                st.info("🌟 Using TOP_P environment variable")

            if use_top_p:
                top_p_input = st.slider(
                    "🎯 Top P",
                    min_value=0.0,
                    max_value=1.0,
                    value=top_p,
                    step=0.05,
                    help="Controls nucleus sampling. Lower values make output more focused.",
                )
            else:
                top_p_input = None
                st.info("⚠️ Top P disabled - model will use default sampling")

            # Display current settings info
            settings_text = f"""
            **Current Settings:**
            • Temperature: {temperature_input}
            • Top P: {"Disabled" if top_p_input is None else top_p_input}
            • Max Tokens: {max_tokens_input}
            """
            st.info(settings_text)

    return temperature_input, top_p_input, max_tokens_input


def auto_connect_model(
    provider: ProviderType,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    top_p: Optional[float],
    max_tokens: int,
    provider_name: str,
) -> bool:
    """Auto-connect to a model and update session state."""
    if not all([api_key, base_url, model]):
        return False

    try:
        # Create model instance
        kwargs = {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,  # Always pass top_p, even if None (so model can filter it out)
            "max_tokens": max_tokens,
        }

        new_model = CustomChatModel(**kwargs)

        # Check if this is a different model
        model_changed = (
            "current_model" not in st.session_state
            or st.session_state.get("current_model_name") != model
            or st.session_state.get("current_provider") != provider_name
        )

        # Store in session state
        st.session_state.current_model = new_model
        st.session_state.current_provider = provider_name
        st.session_state.current_model_name = model

        # Add system message if model changed
        if model_changed and "messages" in st.session_state:
            top_p_display = "Disabled" if top_p is None else f"{top_p}"
            system_msg = f"🔄 **Model Updated** - {provider_name}: `{model}` (T={temperature}, P={top_p_display}, Max={max_tokens})"
            st.session_state.messages.append({"role": "assistant", "content": system_msg})

        return True
    except Exception:
        return False


def render_sidebar() -> Tuple[ProviderType, str, str, str, str, float, Optional[float], int]:
    """Render the sidebar with provider configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Provider selection (always visible)
        selected_provider, selected_provider_name = render_provider_selector()
        provider_configs = get_provider_configs()
        provider_config = provider_configs[selected_provider]

        # Get environment values
        env_api_key, env_base_url, env_model_name, env_temperature, env_top_p, env_max_tokens = get_env_values(
            provider_config, selected_provider
        )

        # Auto-fetch models when provider changes and credentials are available
        should_auto_fetch = (
            env_api_key
            and env_base_url
            and (
                st.session_state.models_provider != selected_provider.value or len(st.session_state.fetched_models) == 0
            )
        )

        if should_auto_fetch:
            with st.spinner("Auto-fetching models..."):
                fetched_models = fetch_models_from_api(env_base_url, env_api_key)
                if fetched_models:
                    st.session_state.fetched_models = fetched_models
                    st.session_state.models_provider = selected_provider.value
                    st.rerun()

        # Collapsible Provider Configuration Section
        with st.expander(f"🔧 {selected_provider_name} Provider", expanded=True):
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

            # Model selection with auto-connect
            selected_model = render_model_selection(selected_provider, provider_config, env_model_name)

        # LLM Configuration Section
        has_top_p_env = bool(os.getenv(provider_config.get("top_p_env", "TOP_P")))
        temperature, top_p, max_tokens = render_llm_configuration(
            env_temperature, env_top_p, env_max_tokens, has_top_p_env
        )

        # Auto-connect when model is selected or LLM parameters change
        should_auto_connect = selected_model and api_key and base_url

        if should_auto_connect:
            # Check if any configuration has changed
            current_config = {
                "model": selected_model,
                "provider": selected_provider_name,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }

            last_config = st.session_state.get("last_config", {})
            config_changed = current_config != last_config

            if config_changed:
                # Show what changed for debugging
                if "last_config" in st.session_state and st.session_state.last_config:
                    old_top_p = st.session_state.last_config.get("top_p")
                    if old_top_p != top_p:
                        top_p_old = "Disabled" if old_top_p is None else f"{old_top_p}"
                        top_p_new = "Disabled" if top_p is None else f"{top_p}"
                        st.info(f"🔄 Top P changed: {top_p_old} → {top_p_new}")

                auto_connect_success = auto_connect_model(
                    selected_provider,
                    api_key,
                    base_url,
                    selected_model,
                    temperature,
                    top_p,
                    max_tokens,
                    selected_provider_name,
                )
                if auto_connect_success:
                    st.success(f"🟢 Connected to **{selected_model}**")
                    st.session_state.last_config = current_config
                else:
                    st.error("❌ Auto-connection failed")

        # Manual test connection (now optional)
        if st.button("🧪 Manual Test Connection"):
            if not all([api_key, base_url, selected_model]):
                st.error("Please fill in all required fields!")
            else:
                success = auto_connect_model(
                    selected_provider,
                    api_key,
                    base_url,
                    selected_model,
                    temperature,
                    top_p,
                    max_tokens,
                    selected_provider_name,
                )
                if success:
                    st.success("✅ Manual connection successful!")
                else:
                    st.error("❌ Manual connection failed!")

        # Current configuration display
        with st.expander("📋 Current Configuration"):
            config_display = {
                "provider": selected_provider.value,
                "api_key": f"{api_key[:8]}..." if api_key else "Not set",
                "base_url": base_url,
                "model": selected_model,
                "temperature": temperature,
                "top_p": "Disabled (None)" if top_p is None else top_p,
                "max_tokens": max_tokens,
            }
            st.json(config_display)

    return selected_provider, selected_provider_name, api_key, base_url, selected_model, temperature, top_p, max_tokens


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
        
        # Optional LLM settings
        export TEMPERATURE=0.7
        # export TOP_P=0.9        # Optional - disabled by default, enable in UI
        export MAX_TOKENS=1000
        ```
        
        **For LLMaaS Dev:**
        ```bash
        export LLM_PROVIDER=llmaas_dev
        export LLMAAS_DEV_API_KEY=your_dev_api_key_here
        export LLMAAS_DEV_BASE_URL=https://dev.api.llmaas.com/v1
        export LLMAAS_DEV_MODEL_NAME=llama33-70b-instruct
        
        # Optional LLM settings
        export TEMPERATURE=0.8
        # export TOP_P=0.95       # Optional - disabled by default, enable in UI
        export MAX_TOKENS=2000
        ```
        
        **For Custom Provider:**
        ```bash
        export LLM_PROVIDER=custom
        export API_KEY=your_custom_api_key_here
        export BASE_URL=https://api.openai.com/v1
        # export MODEL_NAME=gpt-4  # Optional - defaults to "gpt-5-mini"
        
        # Optional LLM settings
        export TEMPERATURE=0.7
        # export TOP_P=0.9        # Optional - disabled by default, enable in UI
        export MAX_TOKENS=1500
        ```
        
        ### Provider Defaults
        If you don't set MODEL_NAME environment variable, these defaults are used:
        - **LLMaaS**: `llama33-70b-instruct`
        - **LLMaaS Dev**: `llama33-70b-instruct` 
        - **Custom**: `gpt-5-mini`
        
        ### LLM Settings Guide
        - **Temperature (0.0-2.0)**: Controls creativity vs consistency
          - 0.0-0.3: Very focused and deterministic
          - 0.7-1.0: Balanced creativity (recommended)
          - 1.5-2.0: Very creative but potentially inconsistent
        
        - **Top P (0.0-1.0)**: Controls token selection diversity ⚠️ **Disabled by default**
          - **Disabled**: Use model's default sampling (recommended for compatibility)
          - 0.1-0.3: Very focused when enabled
          - 0.9: Balanced when enabled
          - 1.0: Consider all tokens when enabled
          - **Note**: Some models don't support top_p, so it's disabled by default
        
        - **Max Tokens**: Maximum response length
          - 500-1000: Short responses
          - 1000-2000: Medium responses (recommended)
          - 2000+: Long responses
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
