"""API service for fetching models from LLM providers."""

import json
from typing import Dict, List

import requests
import streamlit as st


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
