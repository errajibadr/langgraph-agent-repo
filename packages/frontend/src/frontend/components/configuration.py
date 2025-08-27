"""LLM configuration and example configuration UI components."""

import os
from typing import Optional, Tuple

import streamlit as st


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
