# Stream Processor Architecture Documentation

## 🏗️ HIGH-LEVEL ARCHITECTURE

The **ChannelStreamingProcessor** is a sophisticated streaming system that provides real-time monitoring and processing of LangGraph execution. It separates concerns into three distinct streaming domains:

### Core Streaming Domains

1. **Channel Monitoring** - Tracks state changes across all namespaces
2. **Token Streaming** - Streams LLM output token-by-token from specific namespaces  
3. **Tool Call Streaming** - Handles complex tool call argument reconstruction and lifecycle

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                LangGraph Execution                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ Raw Output Stream
                  ▼
┌─────────────────────────────────────────────────────────────┐
│            ChannelStreamingProcessor                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Channel   │  │    Token    │  │     Tool Call       │  │
│  │ Monitoring  │  │  Streaming  │  │     Streaming       │  │
│  │             │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ Structured Events (Stateful with native Deduplication)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                 Event Stream Output                         │
│     TokenStreamEvent | ChannelValueEvent | ToolCallEvent    │
│                       MessageReceivedEvent                  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 HIGH-LEVEL LOGIC FLOW

### 1. Initialization Phase
- **Configure Channels**:
     Define which state keys to monitor (`messages`, `notes`, etc.) 
     Define if this channel is a messageChannel or an artifactChannel
- **Configure Token Streaming**: Specify namespaces for token-by-token streaming
     Maybe we want only to stream token by token for main Graph and avoid Subgraphs.
     Parent graph has a `()` namespace natively in lg that  we translate to `main`.
- **Initialize Handlers**: Set up specialized handlers for different channel types
     MessageChannelHandler: Handles message channels
     ArtifactChannelHandler: Handles artifact channels - For now doesn't handle state of artifacts - re-emits all artifacts continuously at each graph step - we Will want to change this in the future.
     TokenStreamHandler: (Doesn't exist - logic is directly in the processor.py) Handles token streaming 
     ToolCallTracker: (Today namely `ToolCallTracker`) Handles tool call lifecycle  
           - Tool call ( token by token streaming or plain call) 
           - result of tool calls etc.
           - Keeps internal state with tools calls made and result of those tool calls

### 2. Stream Processing Phase
```python
async def stream(graph, input_data, config) -> AsyncGenerator[StreamEvent]:
    # Determine required LangGraph streaming modes
    stream_modes = determine_stream_modes()  # ["values", "messages", etc.]
    
    async for raw_output in graph.astream(input_data, stream_mode=stream_modes):
        # Parse raw output format
        namespace, mode, chunk = parse_raw_output(raw_output)
        
        # Route to appropriate processor
        async for event in process_chunk(namespace, mode, chunk):
            yield event
```

### 3. Event Processing Phase
- **Raw Output Parsing**: Handles all LangGraph output formats (single/multi-mode, subgraphs)
- **Namespace Resolution**: Extracts node names and task IDs from namespaces
- **Event Generation**: Routes chunks to specialized handlers based on mode and channel type

## 🔧 DETAILED COMPONENT BREAKDOWN

## 1. Core Processor (`processor.py`)

### Key Responsibilities
- **Stream Mode Orchestration**: Determines which LangGraph modes to enable
- **Raw Output Parsing**: Handles complex LangGraph output format variations
- **Event Routing**: Delegates processing to specialized handlers
- **State Management**: Tracks previous states and message deduplication

### Raw Output Format Handling
```python
# LangGraph can output in multiple formats:
# 1. Single mode, no subgraphs: chunk or (chunk,metadata) when stream_mode = messages[token by token]
# 2. Multi-mode, no subgraphs: (mode, chunk)  
# 3. Subgraphs + single: (namespace_tuple, chunk)
# 4. Subgraphs + multi: (namespace_tuple, mode, chunk)
```

### Critical Methods
- `_determine_stream_modes()`: Maps configuration to required LangGraph modes
- `_parse_raw_output()`: Normalizes all output formats to (namespace, mode, chunk)
- `_parse_namespace_components()`: Extracts node names and task IDs

## 2. Configuration System (`config.py`)

### ChannelConfig
```python
@dataclass
class ChannelConfig:
    key: str                        # State key to monitor
    stream_mode: StreamMode         # VALUES_ONLY | UPDATES_ONLY  
    channel_type: ChannelType       # MESSAGE | ARTIFACT | GENERIC
    artifact_type: Optional[str]    # UI display type
    filter_fn: Optional[Callable]   # Custom filtering
```

### TokenStreamingConfig
```python
@dataclass  
class TokenStreamingConfig:
    enabled_namespaces: Set[str]    # Which namespaces stream tokens
    message_tags: Optional[Set[str]] # Filter by message tags
    include_tool_calls: bool        # Enable tool call streaming
```

## 3. Event System (`events.py`)

### Event Hierarchy
```python
StreamEvent (base)
├── TokenStreamEvent          # Token-by-token LLM output
├── ChannelValueEvent         # State value changes  
├── ChannelUpdateEvent        # State deltas
├── ArtifactEvent            # Artifact creation/updates
├── MessageReceivedEvent     # Complete message with deduplication
└── ToolCallEvent           # Tool call lifecycle events
```

### Event Data Flow
- **TokenStreamEvent**: Content deltas + accumulated content + message context
- **ArtifactEvent**: Typed artifacts for UI rendering (`Document`, `UserClarification`)
- **ToolCallEvent**: Complex tool call state transitions and argument reconstruction

## 4. Tool Call Streaming System (`tool_calls.py`)

### Complex Pattern Implementation
Tool calls require sophisticated handling due to LangGraph's TOKEN by TOKEN streaming pattern:

Tool calls can then also be found in message channel as we often add the ToolCall and toolResult in the state message Channel as well

1. **First Message**: Contains complete metadata (`id`, `name`, `index`) and can in somecases contain args also
2. **Subsequent Chunks**: Only contain `args` chunks and `index`
```
content='' additional_kwargs={'tool_calls': [{'index': 0, 'id': 'call_a5DCrNmGMCS5bINsY1Dbd6Pt', 'function': {'arguments': '', 'name': 'think_tool'}, 'type': 'function'}]} response_metadata={} id='run--e47d80e7-fb46-4eaf-9199-bce76f066b6c' tool_calls=[{'name': 'think_tool', 'args': {}, 'id': 'call_a5DCrNmGMCS5bINsY1Dbd6Pt', 'type': 'tool_call'}] tool_call_chunks=[{'name': 'think_tool', 'args': '', 'id': 'call_a5DCrNmGMCS5bINsY1Dbd6Pt', 'index': 0, 'type': 'tool_call_chunk'}]
``` 
3. **Linking**: Uses `(message_id, index)` tuple to connect chunks because tool_call_id is not present in the chunks but only in the first message.
```
content='' additional_kwargs={'tool_calls': [{'index': 0, 'id': None, 'function': {'arguments': ' Doe', 'name': None}, 'type': None}]} response_metadata={} id='run--e47d80e7-fb46-4eaf-9199-bce76f066b6c' invalid_tool_calls=[{'name': None, 'args': ' Doe', 'id': None, 'error': None, 'type': 'invalid_tool_call'}] tool_call_chunks=[{'name': None, 'args': ' Doe', 'id': None, 'index': 0, 'type': 'tool_call_chunk'}]
````

4. **JSON Reconstruction**: Incrementally builds and validates JSON arguments

### Tool Call State Machine
```python
class ToolCallStatus:
    INITIALIZING → STREAMING → COMPLETED
                            → ERROR
```

### Key Components
- **ToolCallState**: Tracks individual tool call progression
- **ToolCallTracker**: Manages all active tool calls
- **JSON Validation**: Incremental parsing with error recovery

## 5. Specialized Handlers

### MessageChannelHandler (`message_channel_handler.py`)
- **Purpose**: Process channels containing `BaseMessage` objects
- **Deduplication**: Prevents duplicate events between token streaming and channel monitoring
- **Tool Call Integration**: Links complete messages with tool call lifecycle events

### ArtifactChannelHandler (`artifact_channel_handler.py`)  
- **Purpose**: Handle artifact and generic channels
- **Dual Mode**: Supports both `values` and `updates` processing
- **UI Integration**: Maps channel data to typed artifacts for frontend rendering

## 6. Factory System (`factories.py`)

### Pre-configured Processors
- **`create_simple_processor()`**: Basic setup with sensible defaults
- **`create_message_only_processor()`**: Lightweight message-only monitoring  
- **`create_artifact_processor()`**: Optimized for artifact-based workflows
- **`create_multi_agent_processor()`**: Multi-agent/namespace scenarios
- **`create_debug_processor()`**: Comprehensive monitoring for debugging

## 📊 EVENT FLOW PATTERNS

### 1. Token Streaming Flow
```
LangGraph message chunk → TokenStreamEvent
├── content_delta: "new tokens"
├── accumulated_content: "full content so far"  
├── message_id: "msg_123"
└── namespace: "agent:task_456"
```

### 2. Channel Monitoring Flow  
```
State change → ChannelValueEvent | ArtifactEvent
├── channel: "notes"
├── value/artifact_data: actual content
├── value_delta: what changed
└── namespace context
```

### 3. Tool Call Flow
```
First chunk → ToolCallStartedStreamEvent
Arg chunks → ToolCallProgressStreamEvent (multiple)
Complete   → ToolCallCompletedStreamEvent
Result     → ToolCallEvent(status="result_success")
```
Tool Calls can also be in messageChannel

## 🚀 USAGE PATTERNS

### Basic Usage
```python
from ai_engine.streaming.factories import create_simple_processor

processor = create_simple_processor(
    token_namespaces={"main"},
    include_tool_calls=True
)

async for event in processor.stream(graph, input_data):
    if isinstance(event, TokenStreamEvent):
        print(f"Token: {event.content_delta}")
    elif isinstance(event, ArtifactEvent):
        print(f"Artifact: {event.artifact_type}")
```

### Advanced Configuration
```python
channels = [
    ChannelConfig(key="messages", channel_type=ChannelType.MESSAGE),
    ChannelConfig(key="notes", channel_type=ChannelType.ARTIFACT, artifact_type="Document"),
    ChannelConfig(key="questions", channel_type=ChannelType.ARTIFACT, artifact_type="UserClarification")
]

processor = ChannelStreamingProcessor(
    channels=channels,
    token_streaming=TokenStreamingConfig(
        enabled_namespaces={"agent1", "agent2"},
        include_tool_calls=True
    )
)
```

## 🔍 KEY DESIGN PRINCIPLES

### 1. Separation of Concerns
- **Channel monitoring** is independent of **token streaming**
- **Tool call tracking** operates separately but integrates cleanly
- Each handler has a single, focused responsibility

### 2. Format Normalization
- Handles all LangGraph output format variations transparently
- Provides consistent `(namespace, mode, chunk)` processing interface
- Abstracts away LangGraph streaming complexity

### 3. Event-Driven Architecture
- All outputs are structured events with consistent metadata
- Events are designed for UI consumption and telemetry
- Type-safe event system prevents runtime errors

### 4. Performance Optimization
- **Deduplication**: Prevents duplicate processing of same content
- **Filtering**: Custom filters to reduce unnecessary processing
- **Updates Mode**: Efficient delta-only processing option

### 5. Extensibility  
- **Factory pattern** for common configurations
- **Handler system** allows custom channel processors
- **Event system** supports easy addition of new event types

## 📝 MIGRATION & EVOLUTION

The Stream Processor consolidates and improves functionality from:
- `utils/channel_streaming_v2.py` → Core processor logic
- `utils/streaming_parser.py` → Tool call streaming system

This architecture provides a clean foundation for future streaming enhancements while maintaining backward compatibility through factory functions and configuration options.
```

This documentation provides a comprehensive overview of the Stream Processor architecture, covering both the high-level logic and detailed component breakdown as you requested. The system is designed around clean separation of concerns, robust event handling, and flexible configuration options to support various streaming scenarios from simple token streaming to complex multi-agent tool call processing.