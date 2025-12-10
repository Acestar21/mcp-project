from typing import Optional , Dict
from contextlib import AsyncExitStack
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from ai.ollama import OllamaAI

class MCPClient:
    def __init__(self , config_path : Optional[str] = None):
        if config_path is None:
            config_path = Path("D:\Programming\Projects\mcp-project\client\config\server.json")
        with open(config_path , 'r') as f:
            self.config = json.load(f)
        self.ai = OllamaAI()
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

        # Initialize THIS session (not self.session)
        await session.initialize()

        # STORE THE SESSION CORRECTLY
        self.sessions[server_name] = session

        # Debug print: ensure tools load
        resp = await session.list_tools()
        tools = [t.name for t in resp.tools]
        print(f"[Connected] {server_name}  tools = {tools}")
    
    
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
    

    async def process(self, query: str):
            """
            Process a user query, allowing for sequential/chained tool execution.
            """
            # Maintain a conversation history for this specific task
            messages = [{"role": "user", "content": query}]
            tools = await self.get_all_tools()

            # Allow up to 15 steps to prevent infinite loops
            for _ in range(15):
                # 1. Ask the AI what to do next
                response = self.ai.generate(messages, tools)
                
                if isinstance(response, dict):
                    reply = response["message"]["content"]
                else:
                    reply = response.message.content

                # 2. Check if the AI wants to use a tool (looks for JSON)
                # We assume the AI complies with "Respond ONLY with JSON" for tools
                json_match = re.search(r"\{.*\}", reply, re.DOTALL)
                
                tool_found = False
                
                if json_match:
                    try:
                        call = json.loads(json_match.group())
                        
                        if "tool" in call:
                            tool_found = True
                            full_name = call["tool"]
                            args = call.get("args", {})
                            
                            # Parse "server.tool"
                            if "." in full_name:
                                server_name, tool_name = full_name.split(".", 1)
                            else:
                                # Handle error if AI forgets prefix
                                error_msg = f"Error: Tool '{full_name}' must include server prefix (e.g., 'server.tool')"
                                messages.append({"role": "assistant", "content": reply})
                                messages.append({"role": "system", "content": error_msg})
                                continue # Try again with error info

                            print(f"   [Tool Call] {full_name} with args: {args}")

                            # 3. Execute the tool
                            try:
                                result = await self.call_tool(server_name, tool_name, args)
                                
                                # Convert result to clean string
                                content_str = self.print_response(result)
                            except Exception as tool_err:
                                content_str = f"Error executing tool: {str(tool_err)}"

                            # 4. Update History
                            # We append the AI's "Request" and the System's "Result"
                            messages.append({"role": "assistant", "content": reply})
                            messages.append({
                                "role": "user", 
                                "content": f"[Tool Output from {full_name}]:\n{content_str}"
                            })

                            # 5. Loop continues! 
                            # The code goes back to the top, sends the updated 'messages' to Ollama,
                            # and Ollama decides if it needs *another* tool or if it's done.
                            continue

                    except json.JSONDecodeError:
                        # Found braces but valid JSON, treat as text
                        pass
                    except Exception as e:
                        print(f"Processing Error: {e}")
                
                # If we get here, either:
                # A) No tool was found in the response
                # B) The tool logic finished and we are breaking the loop manually (though the 'continue' handles the loop)
                
                if not tool_found:
                    # The AI replied with normal text (no tool), so we are done.
                    return reply

            return "Error: Maximum task steps exceeded (stuck in loop)."

    async def get_all_tools(self):
        """Return cleaned tool definitions for Ollama."""
        tools = []

        for server_name, session in self.sessions.items():
            resp = await session.list_tools()
            for tool in resp.tools:
                tools.append({
                    "name": f"{server_name}.{tool.name}",
                    "description": tool.description,
                    "parameters": tool.inputSchema  # raw schema works for Ollama
                })

        return tools

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