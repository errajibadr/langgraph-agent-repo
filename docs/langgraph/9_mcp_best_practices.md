# MCP (Model Context Protocol) Best Practices

## Overview

The Model Context Protocol (MCP) enables seamless integration between AI agents and external tools through a standardized client-server architecture.

## Client-Server Architecture

### Basic Model

The MCP architecture consists of three main components:

- **Client**: The `MultiServerMCPClient` acts as the client that requests services
- **Server**: The MCP server provides tools and executes operations  
- **Communication**: They communicate using a standardized protocol (MCP)

```python
client = MultiServerMCPClient(mcp_config)
```

### MultiServerMCPClient Responsibilities

The `MultiServerMCPClient` is our LangChain MCP adapter client that:

- Starts MCP servers based on configuration
- Manages communication with one or more servers
- Converts MCP protocols to LangChain-compatible formats

## Configuration

### MCP Config Structure

The configuration tells the MCP client how to start and connect to MCP servers:

```python
mcp_config = {
    "filesystem": {  # Server name (arbitrary label)
        "command": "npx",  # Command to run
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/docs"],
        "transport": "stdio"  # Communication method
    }
}
```

### Configuration Components

- **Server name** (`"filesystem"`): An arbitrary label for this server instance
- **Command** (`"npx"`): The command to execute to start the server
- **Args**: Command-line arguments passed to the server
- **Transport**: How the client communicates with the server

## Transport Types

### 1. STDIO Transport (Local Servers)

Used for local servers running as subprocesses:

- Uses standard input/output for communication
- Server runs as a subprocess on your local machine
- Communication via pipes (stdin/stdout)
- Example: `"transport": "stdio"`

**Characteristics:**
- ✅ Fast performance
- ✅ Secure (local execution)
- ❌ Requires server installation

### 2. HTTP Transport (Remote Servers)

Used for remote third-party services:

- Uses HTTP requests for communication
- Server runs remotely on another machine/service
- Communication via HTTP endpoints
- Example: `"transport": "http"` with `"url": "https://api.example.com/mcp"`

**Characteristics:**
- ❌ Slower than local
- ❌ Requires trust/authentication
- ✅ No local installation needed

### Remote MCP Servers

Remote MCP servers are third-party services that provide tools via HTTP. According to Anthropic's documentation:

- Companies like **Asana**, **Cloudflare**, **PayPal**, and **Zapier** offer remote MCP servers
- These use HTTP transport instead of stdio
- Typical URL format: `https://mcp.[company-name].com/sse`
- Require authentication credentials and trust verification

#### Example Remote Configuration

```python
mcp_config = {
    "remote_service": {
        "url": "https://mcp.example.com/sse",
        "transport": "http",
        "headers": {
            "Authorization": "Bearer your-token-here"
        }
    }
}
```

## Server Lifecycle Management

### STDIO Transport (Local Servers)

When using stdio transport:

1. **Client** `MultiServerMCPClient(mcp_config)` starts the server as a subprocess
2. **Server** is a Node.js process running on your local machine
3. **Execution**: It runs `npx @modelcontextprotocol/server-filesystem /path/to/docs`
4. **Lifecycle**: The server process runs as long as the client is active

> ✅ **Verified**: The client starts and manages the server process lifecycle

### HTTP Transport (Remote Servers)

When using HTTP transport:

1. **Client** connects to an existing remote server
2. **No subprocess** is started locally
3. **Server** runs independently on remote infrastructure
4. **Communication** happens over HTTP/HTTPS

## Tool Integration

### Tool Discovery

Within the agent, MCP client queries the server for available tools:

```python
tools = await client.get_tools()
```

### The Tool Binding Process

1. **Query**: MCP client queries each server: "What tools do you provide?"
2. **Response**: Server responds with tool metadata (name, description, parameters, types)
3. **Conversion**: The MCP client (adapter) converts tool metadata to LangChain format
4. **Compatibility**: This makes them compatible with LangChain agents
5. **Binding**: We bind the tools to the model as usual:

```python
model_with_tools = model.bind_tools(tools)
```

## Tool Execution Flow

When the LLM calls a tool, the following process occurs:

### 1. Decision Phase
- **LLM Decision**: The LLM decides which tools to use based on the user's request

### 2. Communication Phase
- **Client Forwarding**: The client forwards the request to the appropriate server
- **Communication Methods**:
  - **STDIO**: Via STDIN (for local servers)
  - **HTTP**: Via HTTP requests (for remote servers)

### 3. Execution Phase
- **Server Execution**: The server executes the operation (e.g., reads a file)
- **Async Processing**: This is done asynchronously for performance

### 4. Response Phase
- **Response Delivery**: Server sends responses back to the client
  - **STDIO**: Via STDOUT (for local servers)
  - **HTTP**: Via HTTP responses (for remote servers)
- **Protocol**: All communication uses MCP protocol format (JSON-RPC)

```python
coros.append(tool.ainvoke(tool_call["args"]))
```

## Summary: Transport Comparison

| Aspect | Local (STDIO) | Remote (HTTP-SSE) |
|--------|---------------|---------------|
| **Speed** | Fast | Slower |
| **Security** | Secure (local) | Requires trust/auth |
| **Setup** | Requires server installation | No local installation |
| **Dependencies** | Node.js, npm packages | Internet connection |
| **Use Case** | Development, secure environments | Production, third-party services |
