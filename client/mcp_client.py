from typing import Optional , Dict , Callable, Any
from contextlib import AsyncExitStack
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from ai.ollama import OllamaAI
import sys
import asyncio
import uuid
import time

class MCPClient:
    def __init__(self , config_path : Optional[str] = None):

        base_dir = Path(__file__).parent
        if config_path is None:
            config_path = base_dir / "config" / "server.json"
        with open(config_path , 'r') as f:
            self.config = json.load(f)
        self.ai = OllamaAI()
        self.sessions: Dict[str,ClientSession] = {}
        self.tool_cache: Dict[str, list[Any]] = {}

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
    

    def classify_intent(self, query: str) -> str:
        q = query.lower()
        LOCAL_HINTS = [
            "file", "files", "folder", "directory", "dir",
            "workspace", "project", "stuff", "area", "contents",
            "what's inside", "inside", "working area"
        ]

        WEB_HINTS = [
            "search", "google", "online", "web", "internet", "http", "url"
        ]
        has_web = any(w in q for w in WEB_HINTS)
        has_local = any(w in q for w in LOCAL_HINTS)

        if has_web and has_local:
            return "MIXED"
        if has_web:
            return "WEB"
        if has_local:
            return "LOCAL"
        return "UNKNOWN"


    def filter_tools(self, intent: str) -> list[dict]:
        """Return only tools allowed for the specific intent."""
        allowed = []
        for server, tools in self.tool_cache.items():
            # Define your rules here
            is_web = "browser" in server
            is_local = "file" in server or "mcp" in server
            
            if intent == "WEB" and is_local: continue
            if intent == "LOCAL" and is_web: continue
            
            allowed.extend(tools)
        return allowed


    def check_policy(self, server_name: str, intent: str) -> bool:
        """Final gate check before execution."""
        if intent == "MIXED": return True
        if intent == "WEB" and "file" in server_name: return False
        if intent == "LOCAL" and "browser" in server_name: return False
        return True


    def _emit(self, handler, event_type: str, request_id: str, data: dict = None):
        if not handler: return
        payload = {
            "type": event_type,
            "request_id": request_id,
            "timestamp": time.time(),
            **(data or {})
        }
        handler(payload)


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

        print(f"[Cache] Fetching tools for {server_name}...", file=sys.stderr)
        resp = await session.list_tools()
        
        # Store with server origin metadata
        self.tool_cache[server_name] = []
        for tool in resp.tools:
            self.tool_cache[server_name].append({
                "name": f"{server_name}.{tool.name}",
                "description": tool.description,
                "parameters": tool.inputSchema,
                "server": server_name
            })
    
    
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
    

    async def process(self, query: str, event_handler: Callable[[dict], None] = None):
        """
        Process a user query, allowing for sequential/chained tool execution.
        """
        # 1. Initialize Request & Eventing
        request_id = str(uuid.uuid4())
        self._emit(event_handler, "request_started", request_id, {"query": query})

        # 2. Handle Special Commands
        if query.strip().lower() in ["/clear", "/reset", "/wipe"]:
            return self.clear_memory()
        
        if query.strip().lower() in ["/summarize", "/sum"]:
            return await self.summarize_memory()

        if len(self.history) > 30:
            await self.summarize_memory()

        # 3. Update Memory
        self.history.append({"role": "user", "content": query})
        self.save_memory()

        # 4. Planning & Gating
        self._emit(event_handler, "planning_started", request_id)
        
        intent = self.classify_intent(query)

        # if intent == "MIXED":
        #     self._emit(event_handler, "policy_blocked", request_id, {
        #         "reason": "Conflicting intents: web and local filesystem access in one request."
        #     })
        #     self._emit(event_handler, "request_completed", request_id)
        #     return (
        #         "I can’t combine online actions with local file access in a single request. "
        #         "Please choose one or split the request."
        #     )


        filtered_tools = self.filter_tools(intent) 
        
        self._emit(event_handler, "tool_candidates_resolved", request_id, {
            "intent": intent,
            "tool_count": len(filtered_tools),
            "tools": [t["name"] for t in filtered_tools]
        })

        # 5. Execution Loop
        for step_idx in range(15):
            
            self._emit(event_handler, "step_started", request_id, {
                "step": step_idx + 1,
                "max_steps": 15
            })

            # Generate response using ONLY filtered tools
            response = self.ai.generate(self.history, filtered_tools)
            
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

                        # Validate format
                        if "." in full_name:
                            server_name, tool_name = full_name.split(".", 1)
                        else:
                            error_msg = f"Error: Tool '{full_name}' must include server prefix (e.g., 'server.tool')"
                            self.history.append({"role": "assistant", "content": reply})
                            self.history.append({"role": "system", "content": error_msg})
                            continue 
                        
                        # --- POLICY CHECK ---
                        if not self.check_policy(server_name, intent):
                            block_msg = f"Intent '{intent}' prohibits using tool '{full_name}' from server '{server_name}'."
                            
                            self._emit(event_handler, "policy_blocked", request_id, {
                                "tool": full_name,
                                "reason": block_msg
                            })
                            
                            # Feedback to AI
                            self.history.append({"role": "assistant", "content": reply})
                            self.history.append({"role": "user", "content": f"SYSTEM: {block_msg}"})
                            self.save_memory()
                            self._emit(event_handler, "assistant_message", request_id, {
                                "content": block_msg
                            })
                            self._emit(event_handler, "request_completed", request_id)
                            return block_msg
                        

                        # Notify UI: Tool Starting
                        self._emit(event_handler, "tool_call_started", request_id, {
                            "tool": full_name,
                            "args": args
                        })

                        print(f"   [Tool Call] {full_name} with args: {args}", file=sys.stderr)

                        try:
                            # Execute
                            result = await self.call_tool(server_name, tool_name, args)
                            
                            # Notify UI: Success
                            self._emit(event_handler, "tool_call_succeeded", request_id, {
                                "tool": full_name
                            })

                            content_str = self.print_response(result)
                            
                        except Exception as tool_err:
                            # Notify UI: Failure
                            self._emit(event_handler, "tool_call_failed", request_id, {
                                "tool": full_name,
                                "error": str(tool_err)
                            })
                            content_str = f"Error executing tool: {str(tool_err)}"


                        self.history.append({"role": "assistant", "content": reply})
                        self.history.append({
                            "role": "user", 
                            "content": f"OBSERVATION [Tool Output from {full_name}]:\n{content_str}"
                        })
                        self.save_memory()
                        continue
                    
                except Exception as e:
                    print(f"Processing Error: {e}", file=sys.stderr)
            
            # if intent == "LOCAL" and not tool_found:
            #     refusal = (
            #         "I can’t describe local directory contents without actually "
            #         "reading them using filesystem tools. "
            #         "Please allow me to list the directory."
            #     )

                # self._emit(event_handler, "policy_blocked", request_id, {
                #     "reason": "Local state requested without tool usage."
                # })
                # self._emit(event_handler, "request_completed", request_id)
                # return response
            
            if not tool_found:
                # No tool called, we are done
                self.history.append({"role": "assistant", "content": reply})
                self.save_memory()
                self._emit(event_handler, "assistant_message", request_id, {
                    "content": reply
                })
                self._emit(event_handler, "request_completed", request_id, {
                    "result_length": len(reply)
                })
                return reply

        # Loop finished without return
        self._emit(event_handler, "request_failed", request_id, {"reason": "Max steps exceeded"})
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