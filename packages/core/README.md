# Core Package

Core business logic, models, and shared utilities for the LangGraph Agent Repository.

## 🏗️ Package Structure

```
core/
├── types/
│   └── providers.py    # ProviderType enum and provider-related types
├── models/
│   └── providers.py    # Provider settings and configuration models
└── utils/
    └── env.py          # Environment variable handling utilities
```

## 📦 What's Included

### **Types** (`core.types`)
- `ProviderType`: Enum for supported LLM providers (LLMaaS, LLMaaS Dev, Custom)

### **Models** (`core.models`)
- `BaseProviderSettings`: Base configuration for all providers
- `LLMaaSSettings`: LLMaaS-specific settings with `LLMAAS_` prefix
- `LLMaaSDevSettings`: LLMaaS Dev settings with `LLMAAS_DEV_` prefix  
- `CustomProviderSettings`: Custom provider settings (no prefix)
- `MultiProviderSettings`: Multi-provider configuration management

### **Utilities** (`core.utils`)
- `get_provider_configs()`: Get configuration mapping for all providers
- `get_env_values()`: Extract environment variables with provider defaults

## 🚀 Usage

```python
# Import types
from core.types import ProviderType

# Import models
from core.models import MultiProviderSettings, BaseProviderSettings

# Import utilities
from core.utils import get_provider_configs, get_env_values

# Example usage
settings = MultiProviderSettings()
provider_config = get_provider_configs()[ProviderType.CUSTOM]
env_values = get_env_values(provider_config, ProviderType.CUSTOM)
```

## 🔧 Configuration

The core package supports environment variables for each provider:

### LLMaaS Provider
```bash
export LLMAAS_API_KEY=your_key
export LLMAAS_BASE_URL=https://api.llmaas.com/v1
export LLMAAS_MODEL_NAME=llama33-70b-instruct
```

### LLMaaS Dev Provider  
```bash
export LLMAAS_DEV_API_KEY=your_dev_key
export LLMAAS_DEV_BASE_URL=https://dev.api.llmaas.com/v1
export LLMAAS_DEV_MODEL_NAME=llama33-70b-instruct
```

### Custom Provider
```bash
export API_KEY=your_custom_key
export BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-5-mini
```

### LLM Generation Settings (Optional)
```bash
export TEMPERATURE=0.7
export TOP_P=0.9
export MAX_TOKENS=1000
```

## 🎯 Dependencies

- `pydantic>=2.0.0`: Data validation and settings management
- `pydantic-settings>=2.0.0`: Environment variable configuration
- `python-dotenv>=1.0.0`: .env file support
