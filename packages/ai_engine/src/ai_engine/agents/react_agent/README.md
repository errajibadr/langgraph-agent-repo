# Generic React Agent Architecture

A type-safe, generic React Agent implementation with full LangGraph integration and runtime type validation.

## 🎯 Key Features

- **Full Type Safety**: Generic type parameters with compile-time and runtime validation
- **LangGraph Integration**: Seamless integration with LangGraph's StateGraph system
- **Agent Composition**: Easy composition of agents as tools for other agents
- **Runtime Validation**: Automatic schema validation to prevent runtime errors
- **Clean Architecture**: Modular design with clear separation of concerns
- **Extensible**: Easy to extend with new agent types and behaviors

## 📁 Architecture Overview

```
packages/ai_engine/src/ai_engine/agents/react_agent/
├── __init__.py              # Main exports
├── base.py                  # Generic PydanticReactAgent class
├── types.py                 # Type definitions and common utilities
├── demo.py                  # Comprehensive demonstration script
├── examples/                # Example implementations
│   ├── __init__.py
│   ├── weather_agent.py     # Weather agent with custom schemas
│   └── supervisor_agent.py  # Supervisor agent that delegates to others
└── README.md               # This file
```

## 🔧 Core Components

### 1. Generic Base Class

The `PydanticReactAgent` class is generic with three type parameters:

```python
class PydanticReactAgent(Generic[StateT, InputT, OutputT]):
    """
    Generic React Agent with full type safety.
    
    Type Parameters:
        StateT: Main state schema (required)
        InputT: Input state schema (optional, defaults to StateT)
        OutputT: Output state schema (optional, defaults to StateT)
    """
```

### 2. Type System

```python
# Type variables with proper bounds
StateT = TypeVar("StateT", bound=Union[AgentState, AgentStatePydantic, TypedDict, BaseModel])
InputT = TypeVar("InputT", bound=Union[TypedDict, BaseModel])
OutputT = TypeVar("OutputT", bound=Union[TypedDict, BaseModel])

# Common type aliases
ToolType = Union[BaseTool, Callable[..., Any]]
StateSchemaType = Type[Union[AgentState, AgentStatePydantic, TypedDict, BaseModel]]
```

### 3. Runtime Validation

The system includes automatic validation of state schemas:

```python
def _validate_schemas(self) -> None:
    """Validate that all schemas are compatible and properly defined."""
    # Ensures required fields exist
    # Validates type annotations
    # Checks compatibility with LangGraph
```

## 🚀 Usage Examples

### Basic Agent Creation

```python
from ai_engine.agents.react_agent import PydanticReactAgent
from ai_engine.models.custom_chat_model import CustomChatModel

# Create a simple agent with default schemas
model = CustomChatModel(provider="groq")
agent = PydanticReactAgent(
    name="my_agent",
    model=model,
    tools=[my_tool1, my_tool2],
    state_schema=AgentStatePydantic,
)
```

### Type-Safe Custom Agent

```python
# Define custom schemas
class MyAgentState(BaseModel):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: RemainingSteps = 10
    custom_field: str = ""

class MyInputState(BaseModel):
    query: str
    messages: Annotated[Sequence[BaseMessage], add_messages]

class MyOutputState(BaseModel):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    result: str

# Create type-safe agent
agent: PydanticReactAgent[MyAgentState, MyInputState, MyOutputState] = PydanticReactAgent(
    name="custom_agent",
    model=model,
    tools=[custom_tool],
    state_schema=MyAgentState,
    input_schema=MyInputState,
    output_schema=MyOutputState,
    response_format=MyResponseFormat,
)
```

### Agent Composition

```python
# Create specialized agent
weather_agent = create_weather_agent(model)
weather_graph = weather_agent.get_graph()

# Create supervisor agent that uses weather agent as a tool
@tool
def call_weather_agent(state: Annotated[AgentStatePydantic, InjectedState]) -> str:
    """Delegate weather queries to specialized weather agent."""
    response = weather_graph.invoke(
        InputWeatherAgentStatePydantic(
            messages=[state.messages[0]],
            query="Get weather information",
        )
    )
    return str(response.get("summary"))

supervisor_agent = create_simple_agent(
    name="supervisor",
    model=model,
    tools=[think_tool, call_weather_agent],
)
```

## 🏗️ Design Patterns

### 1. Factory Functions

Use factory functions for common agent patterns:

```python
def create_simple_agent(
    name: str,
    model: CustomChatModel,
    tools: List[ToolType],
    *,
    state_schema: Type[StateT] = AgentStatePydantic,
) -> PydanticReactAgent[StateT, StateT, StateT]:
    """Create agent with same schema for all state types."""
    return PydanticReactAgent(
        name=name,
        model=model,
        tools=tools,
        state_schema=state_schema,
    )
```

### 2. Tool Creation

Create tools that can access agent state:

```python
@tool
def my_tool(state: Annotated[MyStateType, InjectedState]) -> str:
    """Tool that can access the current agent state."""
    # Access state.messages, state.remaining_steps, etc.
    return "Tool result"
```

### 3. Agent Integration

Integrate agents as tools in other agents:

```python
def create_agent_tool(agent_graph, input_schema):
    @tool
    def call_agent(state: Annotated[AgentStatePydantic, InjectedState]) -> str:
        response = agent_graph.invoke(
            input_schema(messages=state.messages, query="Process request")
        )
        return str(response)
    return call_agent
```

## 🔍 Type Safety Benefits

### Compile-Time Checking

IDEs and type checkers can validate:
- Correct state schema usage
- Proper tool signatures
- Valid method calls
- Schema compatibility

### Runtime Validation

The system automatically validates:
- Required fields in state schemas
- Type annotations presence
- Schema compatibility with LangGraph
- Proper inheritance chains

### Example Type Error Prevention

```python
# This will be caught at compile-time by type checkers
agent: PydanticReactAgent[WeatherState, InputState, OutputState] = PydanticReactAgent(
    state_schema=WrongStateType,  # ❌ Type error!
    # ...
)

# This will be caught at runtime during validation
class InvalidState(BaseModel):
    # Missing required 'messages' field
    some_field: str

agent = PydanticReactAgent(
    state_schema=InvalidState,  # ❌ Runtime validation error!
    # ...
)
```

## 🧪 Testing and Validation

Run the comprehensive demo to see all features:

```bash
cd packages/ai_engine/src/ai_engine/agents/react_agent
python demo.py
```

The demo includes:
- Type safety demonstration
- Agent composition examples  
- Runtime validation tests
- Interactive chat example

## 🔄 Migration Guide

### From Old React Agent

```python
# Old approach
class OldReactAgent:
    def __init__(self, state, input_state, output_state, ...):
        # No type safety, runtime errors possible

# New approach  
agent: PydanticReactAgent[StateT, InputT, OutputT] = PydanticReactAgent(
    state_schema=StateT,
    input_schema=InputT,
    output_schema=OutputT,
    # Full type safety and validation
)
```

### Benefits of Migration

1. **Type Safety**: Catch errors at compile-time
2. **Better IDE Support**: Autocomplete and error detection
3. **Runtime Validation**: Prevent schema mismatches
4. **Cleaner Code**: Separation of concerns
5. **Extensibility**: Easy to add new agent types

## 📚 Advanced Usage

### Custom Validation

Extend the base class to add custom validation:

```python
class CustomReactAgent(PydanticReactAgent[StateT, InputT, OutputT]):
    def _validate_schemas(self) -> None:
        super()._validate_schemas()
        # Add custom validation logic
```

### Dynamic Schema Selection

Use factory functions with conditional logic:

```python
def create_adaptive_agent(agent_type: str, model: CustomChatModel):
    if agent_type == "weather":
        return create_weather_agent(model)
    elif agent_type == "research":
        return create_research_agent(model)
    # etc.
```

### Context-Aware Tools

Create tools that adapt based on agent context:

```python
@tool
def adaptive_tool(
    state: Annotated[StateT, InjectedState],
    context: str
) -> str:
    """Tool that adapts behavior based on state and context."""
    if hasattr(state, 'weather_messages'):
        # Weather-specific logic
        pass
    elif hasattr(state, 'research_notes'):
        # Research-specific logic  
        pass
    return "Adaptive result"
```

This architecture provides a solid foundation for building complex, type-safe agent systems while maintaining flexibility and extensibility.
