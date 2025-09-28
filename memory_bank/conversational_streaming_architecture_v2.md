# Conversational Streaming Architecture V2 - Sequential Message Flow

## 🎯 **ARCHITECTURAL DECISION: Sequential Message Structure**

After analyzing the complexities of multi-namespace, multi-agent conversation flows, we've arrived at an elegant **sequential message structure** that preserves natural conversation flow while handling complex tool calls and subgraph execution.

### **Core Principle: Chronological Message Array**
Instead of hierarchical speaker groupings, maintain a flat, chronological array of messages that mirrors the actual conversation flow.

---

## 🏗️ **MESSAGE STRUCTURE SPECIFICATION**

### **Session State Structure**
```python
st.session_state.messages = [
    # User messages
    {
        "id": "msg_1",                    # LangChain message ID
        "role": "user", 
        "content": "Analyze this data and create a comprehensive report",
        "timestamp": "2024-01-01T10:00:00"
    },
    
    # AI messages (from any namespace)
    {
        "id": "msg_2",                    # LangChain message ID
        "namespace": "main",              # Which namespace/agent
        "role": "ai",
        "content": "I'll help you analyze the data...",
        "timestamp": "2024-01-01T10:00:00"
    },
    
    # Tool call entries (inline with conversation)
    {
        "namespace": "main",              # Namespace where tool was called
        "message_id": "msg_2",            # Links to parent AI message
        "tool_call_id": "call_123",       # Unique tool call identifier
        "role": "tool_call",              # Special role for tool calls
        "name": "think_tool",             # Tool name
        "status": "result_success",       # Tool call lifecycle status
        "args": {"reflection": "..."},    # Tool arguments
        "result": "Reflection complete",  # Tool result (when available)
        "timestamp": "2024-01-01T10:00:00"
    },
    
    # Subgraph AI messages
    {
        "id": "msg_3",
        "namespace": "analysis_agent:task_123",  # Subgraph namespace
        "role": "ai", 
        "content": "Analyzing the data...",
        "timestamp": "2024-01-01T10:00:01"
    },
    
    # Subgraph tool calls
    {
        "namespace": "analysis_agent:task_123",
        "message_id": "msg_3",
        "tool_call_id": "call_456", 
        "role": "tool_call",
        "name": "analyze_data_tool",
        "status": "result_success",
        "args": {"query": "deep analysis"},
        "result": "covariance: 12.5, variance: 8.2",
        "timestamp": "2024-01-01T10:00:02"
    },
    
    # Main AI continues conversation
    {
        "id": "msg_4",
        "namespace": "main",
        "role": "ai",
        "content": "Here is a detailed statistic report... covariance: 12.5",
        "timestamp": "2024-01-01T10:00:03"
    }
]
```

---

## 📋 **TOOL CALL STATUS LIFECYCLE**

### **Status Progression**
```python
Tool Call Lifecycle:
1. "args_streaming"  → 🔧 Calling tool_name...
2. "args_completed"  → 🔍 Executing tool_name...  
3. "result_success"  → ✅ tool_name completed: Result preview
4. "result_error"    → ❌ tool_name failed
```

### **Status Display Mapping**
```python
def get_tool_status_display(tool_message):
    """Convert tool call status to user-friendly display."""
    status_map = {
        "args_streaming": f"🔧 Calling {tool_message['name']}...",
        "args_completed": f"🔍 Executing {tool_message['name']}...", 
        "result_success": f"✅ {tool_message['name']} completed: {preview_result(tool_message.get('result', ''))}",
        "result_error": f"❌ {tool_message['name']} failed: {tool_message.get('error', '')}"
    }
    return status_map.get(tool_message["status"], f"🔧 {tool_message['name']}")

def preview_result(result_text, max_length=50):
    """Create a preview of tool result for inline display."""
    if len(str(result_text)) <= max_length:
        return str(result_text)
    return str(result_text)[:max_length] + "..."
```

---

## 🎨 **RENDERING LOGIC**

### **Sequential Conversation Renderer**
```python
def _render_conversational_chat():
    """Render conversation in natural chronological order."""
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            _render_user_message(message)
            
        elif message["role"] == "ai":
            _render_ai_message(message)
            
        elif message["role"] == "tool_call":
            _render_tool_call(message)

def _render_user_message(message):
    """Render user message."""
    with st.chat_message("user"):
        st.markdown(message["content"])

def _render_ai_message(message):
    """Render AI message with proper speaker identification."""
    # Determine speaker and avatar
    speaker = get_speaker_for_namespace(message.get("namespace", "main"))
    avatar = get_avatar(speaker)
    
    with st.chat_message("assistant", avatar=avatar):
        # Speaker identification (if not main AI)
        if speaker != "AI":
            st.caption(f"🤖 {speaker}")
        
        # Message content
        st.markdown(message["content"])

def _render_tool_call(message):
    """Render tool call as inline work indicator."""
    # Tool status display
    tool_display = get_tool_status_display(message)
    st.caption(tool_display)
    
    # Expandable result for completed tools
    if message["status"] == "result_success" and message.get("result"):
        result_text = str(message["result"])
        if len(result_text) > 100:  # Show in expander for long results
            with st.expander(f"View {message['name']} full result", expanded=False):
                st.text(result_text)

def get_speaker_for_namespace(namespace):
    """Map namespace to display name."""
    if namespace in ["main", "()", "", "messages"]:
        return "AI"
    # Convert namespace to display name (analysis_agent:task_123 → Analysis Agent)  
    base_name = namespace.split(':')[0]
    return base_name.replace("_", " ").title()

def get_avatar(speaker):
    """Get emoji avatar for speaker."""
    avatars = {
        "AI": "🤖",
        "Analysis Agent": "📊", 
        "Research Agent": "🔍",
        "Report Generator": "📝",
        "Data Processor": "⚙️"
    }
    return avatars.get(speaker, "🤖")
```

---

## 🏗️ **COMPONENT RESPONSIBILITIES & ARCHITECTURE**

### **Current Implementation vs Designed Architecture**

#### **❌ Current Reality (Mismatch)**
The current `ConversationalStreamAdapter` mixes data and UI responsibilities:

```python
# ConversationalStreamAdapter currently does BOTH:
class ConversationalStreamAdapter:
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []  # Own internal state
        self.current_message_container = None                 # Own UI containers
        
    async def handle_conversational_streaming(self, speaker, event):
        # Updates own internal state
        namespace_state.message_buffer = event.accumulated_content
        # AND creates/updates Streamlit UI directly
        with self.current_message_container:
            st.markdown(event.accumulated_content)
```

#### **✅ Designed Architecture (Clean Separation)**
Clear separation between data building and UI rendering:

```python
# Should build this structure in st.session_state:
st.session_state.messages = [
    {"role": "user", "content": "..."},
    {"id": "msg_1", "namespace": "main", "role": "ai", "content": "..."},
    {"tool_call_id": "call_1", "role": "tool_call", "status": "result_success"}
]
```

### **📋 Division of Responsibilities**

#### **1. ConversationalStreamAdapter** → **Data Layer (Session State Builder)**

**Responsibility**: Process streaming events and update `st.session_state.messages`

```python
class ConversationalStreamAdapter:
    """Processes streaming events and updates sequential message structure."""
    
    async def handle_conversational_streaming(self, speaker: str, event: TokenStreamEvent):
        """Update or create AI message in session state."""
        # Find existing message in session state
        existing_msg = self._find_message_in_session_state(event.message_id, event.namespace)
        
        if existing_msg:
            # Update existing message content (token streaming)
            existing_msg["content"] = event.accumulated_content
        else:
            # Create new AI message in session state
            st.session_state.messages.append({
                "id": event.message_id,
                "namespace": event.namespace,
                "role": "ai", 
                "content": event.accumulated_content,
                "timestamp": datetime.now().isoformat()
            })

    async def handle_conversational_tool_call(self, speaker: str, event: ToolCallEvent):
        """Update or create tool call entry in session state."""
        existing_tool = self._find_tool_call_in_session_state(event.tool_call_id)
        
        if existing_tool:
            # Update existing tool call status/result
            existing_tool["status"] = event.status
            if event.args:
                existing_tool["args"] = event.args
            if event.result:
                existing_tool["result"] = event.result
        else:
            # Create new tool call entry in session state
            st.session_state.messages.append({
                "namespace": event.namespace,
                "message_id": event.message_id,
                "tool_call_id": event.tool_call_id,
                "role": "tool_call",
                "name": event.tool_name,
                "status": event.status,
                "args": event.args,
                "result": event.result,
                "timestamp": datetime.now().isoformat()
            })
    
    def _find_message_in_session_state(self, message_id, namespace):
        """Find existing AI message in session state."""
        for msg in st.session_state.messages:
            if (msg.get("id") == message_id and 
                msg.get("namespace") == namespace and 
                msg.get("role") == "ai"):
                return msg
        return None
    
    def _find_tool_call_in_session_state(self, tool_call_id):
        """Find existing tool call in session state."""
        for msg in st.session_state.messages:
            if (msg.get("tool_call_id") == tool_call_id and 
                msg.get("role") == "tool_call"):
                return msg
        return None
```

**Key Changes from Current Implementation:**
- ❌ Remove: `self.conversation_history`, `self.current_message_container`, UI container management
- ✅ Add: Direct `st.session_state.messages` manipulation
- ✅ Add: Message/tool call finding methods for session state
- ✅ Focus: Pure data layer, no UI concerns

#### **2. Chat Component** → **UI Layer (Session State Renderer)**

**Responsibility**: Render conversation from `st.session_state.messages` in chronological order

```python
def _render_conversational_chat():
    """Render conversation from session state in chronological order."""
    
    # Render all historical messages from session state
    for message in st.session_state.messages:
        if message["role"] == "user":
            _render_user_message(message)
        elif message["role"] == "ai":
            _render_ai_message(message)
        elif message["role"] == "tool_call":
            _render_tool_call(message)
    
    # Handle new user input
    if prompt := st.chat_input("What would you like to ask?"):
        # Add user message to session state
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Start streaming (adapter will update session state)
        _stream_conversational_response(prompt)

def _render_user_message(message):
    """Render user message."""
    with st.chat_message("user"):
        st.markdown(message["content"])

def _render_ai_message(message):
    """Render AI message with proper speaker identification."""
    # Determine speaker and avatar from namespace
    speaker = get_speaker_for_namespace(message.get("namespace", "main"))
    avatar = get_avatar(speaker)
    
    with st.chat_message("assistant", avatar=avatar):
        # Speaker identification (if not main AI)
        if speaker != "AI":
            st.caption(f"🤖 {speaker}")
        
        # Message content
        st.markdown(message["content"])

def _render_tool_call(message):
    """Render tool call as inline work indicator."""
    # Tool status display
    tool_display = get_tool_status_display(message)
    st.caption(tool_display)
    
    # Expandable result for completed tools
    if message["status"] == "result_success" and message.get("result"):
        result_text = str(message["result"])
        if len(result_text) > 100:  # Show in expander for long results
            with st.expander(f"View {message['name']} full result", expanded=False):
                st.text(result_text)
        else:
            # Show short results inline
            st.text(f"Result: {result_text}")

# Helper functions
def get_speaker_for_namespace(namespace):
    """Map namespace to display name."""
    if namespace in ["main", "()", "", "messages"]:
        return "AI"
    # Convert namespace to display name (analysis_agent:task_123 → Analysis Agent)  
    base_name = namespace.split(':')[0]
    return base_name.replace("_", " ").title()

def get_avatar(speaker):
    """Get emoji avatar for speaker."""
    avatars = {
        "AI": "🤖",
        "Analysis Agent": "📊", 
        "Research Agent": "🔍",
        "Report Generator": "📝",
        "Data Processor": "⚙️"
    }
    return avatars.get(speaker, "🤖")

def get_tool_status_display(tool_message):
    """Convert tool call status to user-friendly display."""
    status_map = {
        "args_streaming": f"🔧 Calling {tool_message['name']}...",
        "args_completed": f"🔍 Executing {tool_message['name']}...", 
        "result_success": f"✅ {tool_message['name']} completed",
        "result_error": f"❌ {tool_message['name']} failed"
    }
    return status_map.get(tool_message["status"], f"🔧 {tool_message['name']}")
```

#### **3. Stream Processor Integration** → **Event Router & Lifecycle Manager**

**Responsibility**: Route events to adapter and manage streaming lifecycle

```python
class ConversationalStreamProcessor:
    """Routes events to adapter and manages streaming lifecycle."""
    
    def __init__(self, enabled_namespaces, include_tool_calls, include_artifacts):
        # Configure underlying stream processor
        self.processor = ChannelStreamingProcessor(...)
        
        # Initialize adapter (data layer)
        self.adapter = ConversationalStreamAdapter()
    
    async def stream_with_conversation(self, graph, input_data, config):
        """Stream events and route to adapter for session state updates."""
        
        async for event in self.processor.stream(graph, input_data, config):
            # Route event to adapter (which updates st.session_state.messages)
            await self.adapter.process_event(event)
            
            # Yield event for any additional processing
            yield event
    
    def reset_session(self):
        """Reset streaming session."""
        # Reset processor state
        self.processor._previous_state.clear()
        self.processor._message_accumulators.clear()
        self.processor._seen_message_ids.clear()
        self.processor.tool_call_tracker.reset()
        
        # Adapter doesn't need reset (works with session state)
```

### **🔄 Complete Architecture Flow**

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────────┐
│   User Input    │    │   Stream Events      │    │   Session State         │
│                 │    │                      │    │                         │
│ "Analyze data"  │───▶│ TokenStreamEvent     │───▶│ st.session_state        │
└─────────────────┘    │ ToolCallEvent        │    │ .messages = [           │
                       │ MessageReceivedEvent │    │   {"role": "user"...    │
                       │ ArtifactEvent        │    │   {"role": "ai"...      │
                       └──────────────────────┘    │   {"role": "tool_call"  │
                                  │                │ ]                       │
                                  ▼                └─────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────┐                      
│                    COMPONENT RESPONSIBILITIES                            │
├──────────────────────────────────────────────────────────────────────────┤
│ 1. ConversationalStreamAdapter (DATA LAYER)                             │
│    ✅ Process events → Update st.session_state.messages                 │
│    ✅ Handle message deduplication by message_id + namespace             │ 
│    ✅ Handle tool call updates by tool_call_id                          │
│    ❌ NO UI concerns, NO container management                            │
├──────────────────────────────────────────────────────────────────────────┤
│ 2. Chat Component (UI LAYER)                                            │
│    ✅ Render st.session_state.messages sequentially                     │
│    ✅ Handle user input → Add to session state                          │
│    ✅ Speaker identification, avatars, tool status display              │
│    ❌ NO direct event processing                                         │
├──────────────────────────────────────────────────────────────────────────┤
│ 3. Stream Processor Integration (EVENT ROUTER)                          │
│    ✅ Route stream events to adapter                                     │
│    ✅ Manage streaming lifecycle                                         │
│    ✅ Session reset coordination                                         │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          UI RENDERING                                   │
│                                                                         │
│ 👤 Human: "Analyze this data..."                                       │
│                                                                         │
│ 🤖 AI: "I'll help you analyze the data..."                            │
│     🔧 Calling analysis_agent...                                        │
│                                                                         │
│ 🤖 Analysis Agent: "Processing your data now..."                       │
│     🔧 Calling data_processor...                                        │
│     ✅ data_processor completed: "Found 3 trends"                      │
│                                                                         │
│ 🤖 AI: "Here's your complete analysis!" + 📋 Artifacts                │
└─────────────────────────────────────────────────────────────────────────┘
```

### **⚠️ Required Implementation Changes**

#### **ConversationalStreamAdapter Changes:**
```python
# REMOVE these current implementations:
- self.conversation_history: List[Dict[str, Any]] = []
- self.current_message_container: Optional[Any] = None  
- self.current_work_container: Optional[Any] = None
- await self.start_new_speaker_turn(speaker)
- with self.current_message_container: st.markdown(...)

# ADD these new implementations:
+ Direct st.session_state.messages manipulation
+ _find_message_in_session_state() method
+ _find_tool_call_in_session_state() method  
+ Pure data processing, no UI concerns
```

#### **Chat Component Changes:**
```python
# REMOVE current simple message display:
- for message in st.session_state.messages:
-     if message["role"] == "user":
-         with st.chat_message("user"): st.markdown(message["content"])

# ADD rich sequential renderer:
+ _render_user_message(message)
+ _render_ai_message(message) with speaker identification
+ _render_tool_call(message) with status display
+ get_speaker_for_namespace() helper
+ get_tool_status_display() helper
```

### **✅ Architecture Benefits**

#### **1. Clean Separation of Concerns**
- **Data Layer**: Pure event processing and session state management
- **UI Layer**: Pure rendering and user interaction
- **Event Router**: Pure event flow and lifecycle management

#### **2. Maintainable & Testable**
- Each component has single responsibility
- Data layer can be unit tested independently
- UI layer focuses only on rendering logic
- Clear interfaces between components

#### **3. Streamlit-Friendly**
- Session state as single source of truth
- Natural rerun behavior handling
- Proper UI container management
- No conflicting state management

#### **4. Real-Time Streaming**
- Adapter updates session state during streaming
- UI renders current state on each rerun
- Natural token-by-token updates
- Tool call status progression

---

## 🔄 **EVENT PROCESSING LOGIC**

### **ConversationalStreamAdapter Implementation**

```python
class ConversationalStreamAdapter:
    """Processes streaming events and updates sequential message history."""
    
    async def handle_conversational_streaming(self, speaker: str, event: TokenStreamEvent):
        """Update or create AI message in chronological order."""
        
        # Find existing message with this message_id and namespace
        existing_msg = self._find_message_by_id_and_namespace(
            event.message_id, event.namespace
        )
        
        if existing_msg:
            # Update existing message content (token streaming)
            existing_msg["content"] = event.accumulated_content
            self._trigger_ui_update(existing_msg)
        else:
            # Create new AI message
            new_message = {
                "id": event.message_id,
                "namespace": event.namespace,
                "role": "ai", 
                "content": event.accumulated_content,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(new_message)
            self._trigger_ui_update(new_message)

    async def handle_conversational_tool_call(self, speaker: str, event: ToolCallEvent):
        """Update or create tool call entry in chronological order."""
        
        # Find existing tool call entry
        existing_tool = self._find_tool_call_by_id(event.tool_call_id)
        
        if existing_tool:
            # Update existing tool call status/result
            existing_tool["status"] = event.status
            if event.args:
                existing_tool["args"] = event.args
            if event.result:
                existing_tool["result"] = event.result
            self._trigger_ui_update(existing_tool)
        else:
            # Create new tool call entry
            new_tool_call = {
                "namespace": event.namespace,
                "message_id": event.message_id,
                "tool_call_id": event.tool_call_id,
                "role": "tool_call",
                "name": event.tool_name,
                "status": event.status,
                "args": event.args,
                "result": event.result,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(new_tool_call)
            self._trigger_ui_update(new_tool_call)

    def _find_message_by_id_and_namespace(self, message_id, namespace):
        """Find message by ID and namespace."""
        for msg in st.session_state.messages:
            if (msg.get("id") == message_id and 
                msg.get("namespace") == namespace and 
                msg.get("role") == "ai"):
                return msg
        return None

    def _find_tool_call_by_id(self, tool_call_id):
        """Find tool call by tool_call_id."""
        for msg in st.session_state.messages:
            if (msg.get("tool_call_id") == tool_call_id and 
                msg.get("role") == "tool_call"):
                return msg
        return None

    def _trigger_ui_update(self, message):
        """Trigger UI update for message (placeholder for real-time updates)."""
        # This will be implemented to update specific UI elements
        # without full page rerun
        pass
```

---

## 🎯 **CONVERSATION FLOW EXAMPLES**

### **Simple Tool Use**
```
👤 Human: "What's in this file?"

🤖 AI: "I'll check that file for you..."
    🔧 Calling file_reader...
    🔍 Executing file_reader...
    ✅ file_reader completed: "Python script with 3 functions"

🤖 AI: "The file contains a Python script with the following functions: [details]"
```

**Message Array:**
```python
[
    {"role": "user", "content": "What's in this file?"},
    {"id": "msg_1", "namespace": "main", "role": "ai", "content": "I'll check that file for you..."},
    {"tool_call_id": "call_1", "role": "tool_call", "name": "file_reader", "status": "result_success", "result": "Python script with 3 functions"},
    {"id": "msg_2", "namespace": "main", "role": "ai", "content": "The file contains a Python script with the following functions: [details]"}
]
```

### **Multi-Agent Conversation**
```
👤 Human: "Analyze this data and create visualizations"

🤖 AI: "I'll coordinate the analysis and visualization for you..."
    🔧 Calling analysis_agent...

🤖 Analysis Agent: "Processing your data now..."
    🔧 Calling data_processor...
    ✅ data_processor completed: "Found 3 key trends"
    "Analysis complete! Found 3 key trends in the data."

🤖 AI: "Now creating visualizations based on the analysis..."
    🔧 Calling visualization_agent...

🤖 Visualization Agent: "Creating charts and graphs..."
    "Generated bar chart... Created trend analysis..."

🤖 AI: "Here's your complete analysis with visualizations!" + 📋 Charts
```

---

## ✅ **ARCHITECTURE BENEFITS**

### **1. Natural Conversation Flow**
- ✅ **Chronological Order**: Messages appear in the order they actually occur
- ✅ **Tool Calls Inline**: Work indicators appear exactly where tools are called
- ✅ **Speaker Transitions**: Smooth handoffs between main AI and agents

### **2. Simple Implementation**
- ✅ **Flat Array Structure**: Easy to iterate and render
- ✅ **Event Processing**: Clear mapping from events to message updates
- ✅ **UI Logic**: Simple sequential rendering

### **3. Real-Time Updates**
- ✅ **Token Streaming**: Update existing messages as tokens arrive
- ✅ **Tool Status**: Update tool call status as lifecycle progresses
- ✅ **Result Integration**: Add results to existing tool call entries

### **4. Deduplication Handling**
- ✅ **Message ID**: Use LangChain message_id to find existing messages
- ✅ **Tool Call ID**: Use tool_call_id to update existing tool calls
- ✅ **No Duplicates**: TokenStreamEvent and MessageReceivedEvent handled correctly

---

## 🔧 **IMPLEMENTATION PRIORITIES**

### **Phase 1: Core Structure** ✅ 
- Sequential message array in session state
- Basic event processing (TokenStreamEvent, ToolCallEvent)
- Simple sequential renderer

### **Phase 2: Enhanced Features**
- Real-time UI updates without full rerun
- Artifact integration inline with speakers
- Tool result expandable displays

### **Phase 3: Polish**
- Performance optimization for long conversations
- Memory cleanup strategies
- Advanced error handling

---

## 📝 **TECHNICAL SPECIFICATIONS**

### **Required Event Types**
- `TokenStreamEvent`: For AI message content updates
- `ToolCallEvent`: For tool call status and result updates  
- `MessageReceivedEvent`: For deduplication handling
- `ArtifactEvent`: For inline artifact display

### **Key Data Structures**
- `st.session_state.messages`: Sequential message array
- Message roles: `user`, `ai`, `tool_call`
- Tool call statuses: `args_streaming`, `args_completed`, `result_success`, `result_error`

### **UI Components**
- Sequential message renderer
- Speaker identification system
- Tool call status display
- Expandable result sections

---

This architecture provides the foundation for natural conversational streaming that handles the full complexity of multi-agent, multi-tool execution while maintaining an intuitive user experience.
