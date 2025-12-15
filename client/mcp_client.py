from typing import Optional , Dict
from contextlib import AsyncExitStack
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from ai.ollama import OllamaAI
import sys

class MCPClient:
    def __init__(self , config_path : Optional[str] = None):

        base_dir = Path(__file__).parent
        if config_path is None:
            config_path = base_dir / "config" / "server.json"
        with open(config_path , 'r') as f:
            self.config = json.load(f)
        self.ai = OllamaAI()
        self.sessions: Dict[str,ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.project_root = base_dir.parent


        self.history_file = base_dir / "history.json"
        self.history = self.load_memory()


    def load_memory(self):
        """Load history from file if it exists."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    print(f"[Memory] Loaded {len(data)} previous messages.",file=sys.stderr)
                    return data
            except Exception as e:
                print(f"[Memory] Error loading file: {e}",file=sys.stderr)
        return []
    

    def save_memory(self):
        """Save current history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"[Memory] Error saving file: {e}",file=sys.stderr)


    def clear_memory(self):
        """Wipe the history."""
        self.history = []
        self.save_memory()
        return "Memory cleared. I have forgotten everything."
    

    async def summarize_memory(self):
        """Compress the history to save space."""
        # Only summarize if we actually have enough content to compress
        if len(self.history) < 4:
            return "History is too short to summarize."

        print("[Memory] Auto-summarizing conversation to prevent overflow...",file=sys.stderr)
        
        # Strategy Keep the System Prompt (implied) + Last 2 turns (User/Assistant or Tool).
        # Compress everything older than that.
        # This ensures the 'immediate' context (like the question just asked) is never lost.
        to_summarize = self.history[:-2] 
        recent_context = self.history[-2:]

        summary_prompt = [
            {"role": "system", "content": "Summarize the following technical conversation. Preserve key technical details, file names, errors, and outcomes. Be concise."},
            {"role": "user", "content": json.dumps(to_summarize)}
        ]

        # Call AI without tools for the summary
        response = self.ai.generate(summary_prompt, []) 
        
        if isinstance(response, dict):
            summary_text = response["message"]["content"]
        else:
            summary_text = response.message.content

        # Reconstruct History: [Summary Node] + [Recent Context]
        # This effectively moves old data to "Long-Term Memory" (the summary)
        # and keeps "Short-Term Memory" (recent context) active.
        new_history = [
            {"role": "system", "content": f"PREVIOUS CONVERSATION SUMMARY: {summary_text}"},
        ] + recent_context

        self.history = new_history
        self.save_memory()
        return f"Memory summarized. Reduced from {len(to_summarize) + 2} messages to {len(self.history)}."

    @staticmethod
    def extract_first_json(text: str):
        """
        Finds the first valid JSON object by counting braces.
        Returns the JSON dict or None.
        """
        text = text.strip()
        idx = text.find("{")
        if idx == -1:
            return None
        
        # Start scanning from the first '{'
        balance = 0
        start = idx
        for i, char in enumerate(text[start:], start=start):
            if char == "{":
                balance += 1
            elif char == "}":
                balance -= 1
                
            # When balance hits zero, we found the closing brace for the outer object
            if balance == 0:
                snippet = text[start : i + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    # If valid structure but invalid syntax, keep searching or fail
                    return None
                    
        return None


    async def connect_to_server(self, server_name: str):
        """Connect to an MCP server

        Args:
            server_name: Name of the server defined in servers.json
        """
        cfg = self.config["servers"][server_name]
        script_path = self.project_root / cfg["args"][0]
        
        # Reconstruct args with the absolute path
        final_args = [str(script_path)] + cfg["args"][1:]


        server_params = StdioServerParameters(
            command=cfg["command"],
            args=final_args,
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdin, stdout = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdin, stdout))

        # Initialize THIS session (not self.session)
        await session.initialize()

        # STORE THE SESSION CORRECTLY
        self.sessions[server_name] = session

    
    
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
            if query.strip().lower() in ["/clear", "/reset", "/wipe"]:
                return self.clear_memory()
            
            if query.strip().lower() in ["/summarize", "/sum"]:
                return await self.summarize_memory()
    
            if len(self.history) > 30:
                await self.summarize_memory()


            self.history.append({"role": "user", "content": query})
            self.save_memory()


            tools = await self.get_all_tools()
            for _ in range(15):

                response = self.ai.generate(self.history, tools)
                
                if isinstance(response, dict):
                    reply = response["message"]["content"]
                else:
                    reply = response.message.content


                tool_data = self.extract_first_json(reply)
                
                tool_found = False
                
                if tool_data:
                    try:
                        call = tool_data
                        
                        if "tool" in call:
                            tool_found = True
                            full_name = call["tool"]
                            args = call.get("args", {})
                            

                            if "." in full_name:
                                server_name, tool_name = full_name.split(".", 1)
                            else:
                                error_msg = f"Error: Tool '{full_name}' must include server prefix (e.g., 'server.tool')"
                                self.history.append({"role": "assistant", "content": reply})
                                self.history.append({"role": "system", "content": error_msg})
                                continue # Try again with error info

                            print(f"   [Tool Call] {full_name} with args: {args}",file=sys.stderr)

                
                            try:
                                result = await self.call_tool(server_name, tool_name, args)

                                content_str = self.print_response(result)
                            except Exception as tool_err:
                                content_str = f"Error executing tool: {str(tool_err)}"


                            self.history.append({"role": "assistant", "content": reply})
                            self.history.append({
                                "role": "user", 
                                "content": f"OBSERVATION [Tool Output from {full_name}]:\n{content_str}"
                            })
                            self.save_memory()
                            continue
                        
                    except Exception as e:
                        print(f"Processing Error: {e}",file=sys.stderr)
                
                
                if not tool_found:
                
                    self.history.append({"role": "assistant", "content": reply})
                    self.save_memory()
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