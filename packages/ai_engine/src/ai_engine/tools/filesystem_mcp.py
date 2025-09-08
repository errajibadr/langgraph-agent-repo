# MCP server configuration for filesystem access

import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR")

mcp_config = {
    "filesystem": {
        "command": "npx",
        "args": [
            "-y",  # Auto-install if needed
            "@modelcontextprotocol/server-filesystem",
            str(ARTIFACT_DIR),  # Path to research documents
        ],
        "transport": "stdio",  # Communication via stdin/stdout
    }
}

# Global client variable - will be initialized lazily
_client = None


def get_mcp_client():
    """Get or initialize MCP client lazily to avoid issues with LangGraph Platform."""
    global _client
    if _client is None:
        _client = MultiServerMCPClient(mcp_config)  # type: ignore
    return _client


async def get_tools():
    client = get_mcp_client()
    tools = await client.get_tools()
    print([tool.name for tool in tools])
    return tools


if __name__ == "__main__":
    import asyncio

    asyncio.run(get_tools())
