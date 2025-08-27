# Multi-Provider LLM Frontend

A Streamlit-based web interface for testing and interacting with multiple LLM providers using the CustomChatModel.

## Features

- 🔄 **Multi-Provider Support**: Switch between LLMaaS, LLMaaS Dev, and Custom providers
- 🔍 **Model Discovery**: Automatically fetch available models from each provider's API
- ⚙️ **Environment Integration**: Automatically loads configuration from environment variables
- 💬 **Interactive Chat**: Real-time chat interface with your selected LLM
- 🧪 **Connection Testing**: Test provider connections before starting a chat session

## Quick Start

### 1. Installation

The frontend package should be installed as part of the main project. If running independently:

```bash
uv add streamlit requests python-dotenv ai-engine
```

### 2. Configuration

Set up your environment variables for the providers you want to use:

#### LLMaaS Provider
```bash
export LLM_PROVIDER=llmaas
export LLMAAS_API_KEY=your_api_key_here
export LLMAAS_BASE_URL=https://api.llmaas.com/v1
export LLMAAS_MODEL_NAME=llama33-70b-instruct
```

#### LLMaaS Dev Provider
```bash
export LLM_PROVIDER=llmaas_dev
export LLMAAS_DEV_API_KEY=your_dev_api_key_here
export LLMAAS_DEV_BASE_URL=https://dev.api.llmaas.com/v1
export LLMAAS_DEV_MODEL_NAME=llama33-70b-instruct
```

#### Custom Provider (e.g., OpenAI)
```bash
export LLM_PROVIDER=custom
export API_KEY=your_openai_api_key_here
export BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-3.5-turbo
```

### 3. Running the Frontend

```bash
uv run frontend
```

This will start the Streamlit application at `http://localhost:8501`

## Usage

1. **Select Provider**: Choose your LLM provider from the sidebar dropdown
2. **Configure Settings**: Enter or verify your API credentials and endpoints
3. **Fetch Models**: Click "Fetch Available Models" to see what models are available
4. **Test Connection**: Verify your configuration works with "Test Connection"
5. **Start Chatting**: Once connected, use the chat interface to interact with your LLM

## Environment Variables

The frontend automatically loads configuration from environment variables:

| Provider | API Key | Base URL | Model Name |
|----------|---------|----------|------------|
| LLMaaS | `LLMAAS_API_KEY` | `LLMAAS_BASE_URL` | `LLMAAS_MODEL_NAME` |
| LLMaaS Dev | `LLMAAS_DEV_API_KEY` | `LLMAAS_DEV_BASE_URL` | `LLMAAS_DEV_MODEL_NAME` |
| Custom | `API_KEY` | `BASE_URL` | `MODEL_NAME` |

You can also set `LLM_PROVIDER` to automatically select the default provider.

## Troubleshooting

### Connection Issues
- Verify your API key is correct and has the necessary permissions
- Ensure the base URL is accessible and ends with `/v1` for OpenAI-compatible APIs
- Check that the model name exists on the provider's platform

### Import Errors
- Make sure the `ai-engine` package is installed and accessible
- Verify you're running from the correct Python environment

### Model Fetching Issues
- Some providers may not support the `/v1/models` endpoint
- In such cases, manually enter the model name in the text input field

## Development

To run the Streamlit app directly for development:

```bash
streamlit run packages/frontend/app.py
```

## Dependencies

- `streamlit>=1.28.0`: Web interface framework
- `requests>=2.31.0`: HTTP client for API calls
- `python-dotenv>=1.0.0`: Environment variable loading
- `ai-engine`: Custom chat model implementation
