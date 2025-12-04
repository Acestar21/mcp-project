from typing import Optional , Dict
from contextlib import AsyncExitStack
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path


class MCPClient:
    def __init__(self , config_path : Optional[str] = None):
        if config_path is None:
            config_path = Path("../client/config/server.json")
        with open(config_path , 'r') as f:
            self.config = json.load(f)

        self.sessions: Dict[str,ClientSession] = {}
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_name: str):
        """Connect to an MCP server

        Args:
            server_name: Name of the server defined in servers.json
        """

        cfg = self.config["servers"][server_name]
        server_params = StdioServerParameters(
            command=cfg["command"],
            args=cfg["args"],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdin, stdout = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdin, stdout))
        await session.initialize()

        self.sessions[server_name] = session

        response = await session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    
    async def connect_all(self):
        """Connect to all servers listed in the config."""
        for server_name in self.config["servers"]:
            await self.connect_to_server(server_name)

    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


    async def call_tool(self, server_name: str, tool_name: str, args: dict):
        """Call a tool on a specific server"""

        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' is not connected.")
        
        session = self.sessions[server_name]
        response = await session.call_tool(tool_name, args)
        return response
    
    @staticmethod
    def print_response(result):
        """Print the response from a tool call"""
        """Extract human-readable text from an MCP tool result."""
        if not result or not result.content:
            return ""

        parts = []
        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))

        return "\n".join(parts)