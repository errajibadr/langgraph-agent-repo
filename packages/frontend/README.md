# Frontend Package

A modular Streamlit application for testing and interacting with different LLM providers.

## 🏗️ Package Structure

```
frontend/
├── components/              # 🎨 UI Components
│   ├── __init__.py         # Component exports
│   ├── chat.py             # Chat interface component
│   ├── configuration.py    # LLM settings & example configs
│   ├── provider.py         # Provider selection & model management
│   └── sidebar.py          # Complete sidebar orchestration
├── services/               # ⚙️ Business Logic Services  
│   ├── __init__.py         # Service exports
│   ├── api.py              # API calls for model fetching
│   ├── model.py            # Model connection & management
│   └── session.py          # Streamlit session state management
└── app.py                  # 🚀 Main entry point (37 lines!)
```

## 📦 What's Included

### **Services** (`frontend.services`)
- **`api.py`**: External API calls (fetch models from OpenAI-compatible endpoints)
- **`session.py`**: Streamlit session state initialization and management  
- **`model.py`**: LLM model connection, auto-connect logic, and session updates

### **Components** (`frontend.components`)
- **`provider.py`**: Provider selection dropdown and model selection interface
- **`configuration.py`**: LLM parameter controls (temperature, top_p, max_tokens) and help documentation
- **`chat.py`**: Main chat interface with message history and response generation
- **`sidebar.py`**: Complete sidebar orchestration combining all provider configuration

### **Main Application** (`app.py`)
- Clean, focused entry point that orchestrates all components
- **575+ lines → 37 lines** 🎉

## 🚀 Usage

### Running the Application
```bash
# From project root
uv run frontend

# Or with Streamlit directly  
streamlit run packages/frontend/src/frontend/app.py
```

### Import Structure
```python
# Clean component imports
from frontend.components import render_chat_interface, render_sidebar
from frontend.services import init_session_state

# Individual component imports
from frontend.components.provider import render_provider_selector
from frontend.services.api import fetch_models_from_api
```

## 🔧 Configuration

The frontend integrates with the `core` package for:
- **Provider Types**: `ProviderType` enum (LLMaaS, LLMaaS Dev, Custom)
- **Configuration**: Environment variable handling and provider configs
- **Settings**: LLM generation parameters and validation

### Environment Variables

See the [core package documentation](../shared/README.md) for complete environment variable reference.

**Quick Setup:**
```bash
# For Custom provider (OpenAI-compatible)
export API_KEY=your_api_key
export BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4  # Optional - defaults to "gpt-5-mini"

# Optional LLM settings
export TEMPERATURE=0.7
export MAX_TOKENS=1000
# export TOP_P=0.9  # Optional - disabled by default
```

## 🎯 Key Features

### **Auto-Connect Behavior**
- ✅ **Auto-fetch models** when provider changes and credentials are available
- ✅ **Auto-connect** when model is selected or LLM parameters change  
- ✅ **Real-time updates** with visual feedback in chat interface

### **Session Management**
- ✅ **Persistent model selection** across provider changes
- ✅ **Chat history** maintained throughout session
- ✅ **Configuration tracking** to detect changes and trigger reconnection

### **UI/UX Enhancements**  
- ✅ **Collapsible sections** for clean organization
- ✅ **Environment variable hints** with clear labeling
- ✅ **Provider-specific defaults** for smooth experience
- ✅ **Optional top_p parameter** (disabled by default for compatibility)

## 🔄 Migrating from Old Structure

The refactoring maintains **100% API compatibility**. All functionality remains the same, just better organized:

| **Old Location** | **New Location** | **Change** |
|------------------|------------------|------------|
| `app.py` (575+ lines) | Multiple files | Broken into logical components |
| All functions in one file | `services/` + `components/` | Separated by responsibility |
| Monolithic imports | Clean, targeted imports | Better dependency management |

## 🧪 Testing

With the modular structure, you can now test components individually:

```python
# Test API service
from frontend.services.api import fetch_models_from_api

# Test UI components  
from frontend.components.provider import render_provider_selector

# Test session management
from frontend.services.session import init_session_state
```

## 🎨 Adding New Components

Follow the established patterns:

1. **Services**: Add to `services/` for business logic
2. **Components**: Add to `components/` for UI elements  
3. **Export**: Update `__init__.py` files for clean imports
4. **Import**: Use in `app.py` or other components as needed

## 🔗 Dependencies

- **Core Dependencies**: `streamlit`, `requests`, `python-dotenv`
- **Internal Dependencies**: `ai-engine` (model wrapper), `core` (settings & types)
- **Architecture**: Modular, service-oriented design following Streamlit best practices