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
            Process a user query, execute tools if needed, and return a natural language response.
            """
            messages = [{"role": "user", "content": query}]
            tools = await self.get_all_tools()

            response = self.ai.generate(messages, tools)
            if isinstance(response, dict):
                reply = response["message"]["content"]
            else:
                reply = response.message.content

            # 2. Check if the AI wants to use a tool (looks for JSON)
            try:
                json_match = re.search(r"\{.*\}", reply, re.DOTALL)
                if json_match:
                    call = json.loads(json_match.group())

                    if "tool" in call:
                        full_name = call["tool"]
                        args = call.get("args", {})
                        
                        # Parse "server.tool" -> "server", "tool"
                        if "." in full_name:
                            server_name, tool_name = full_name.split(".", 1)
                        else:
                            # Fallback if AI forgets the prefix
                            # You might need logic here to find the right server, 
                            # but for now let's assume it provides it correctly or fail gracefully
                            return f"Error: Tool name '{full_name}' must be in format 'server.tool'"

                        print(f"   [Tool Call] {full_name} with args: {args}")

                        # 3. Execute the tool
                        result = await self.call_tool(server_name, tool_name, args)
                        
                        # Convert result to string
                        content_str = ""
                        if hasattr(result, 'content'):
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    content_str += item.text + "\n"
                                else:
                                    content_str += str(item) + "\n"
                        else:
                            content_str = str(result)

                        tool_output = f"[Tool Result from {full_name}]:\n{content_str}"

                        # 4. FEEDBACK LOOP: 
                        # We add the AI's intent and the Tool's actual result to the history
                        messages.append({"role": "assistant", "content": reply})
                        messages.append({
                            "role": "system", 
                            # STRICTER INSTRUCTION HERE:
                            "content": f"[System: The tool execution succeeded. Here is the result.]\n{tool_output}\n\n[Instruction: Summarize this result for the user in natural language. Do not dump the raw JSON.]"
                        })
                        # 5. Ask the AI again: "Given this tool output, what is the answer?"
                        final_response = self.ai.generate(messages, tools)
                        return final_response["message"]["content"]

            except Exception as e:
                print(f"Error processing tool call: {e}")
                # If something breaks, at least return the raw text so we see what happened
                return reply

            # If no tool was called, just return the AI's chat response
            return reply

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