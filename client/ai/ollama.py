import ollama
import json

class OllamaAI:
    def __init__(self, model="qwen2.5:latest"):
        self.model = model

    def generate(self, messages, tools):
        # Build extremely explicit system instructions for local LLM
        system_msg = """
You are an AI assistant that MUST use the provided tools to answer queries.

RULES:
- If a tool should be used, respond ONLY with JSON:
    {"tool": "<server>.<tool>", "args": { ... }}
- DO NOT invent tool names.
- DO NOT answer normally if a tool exists for the query.
- DO NOT guess missing args — ask the user.
- You can call ANY tool listed below.

AVAILABLE TOOLS:
"""

        for t in tools:
            system_msg += f"""
TOOL NAME: {t['name']}
DESCRIPTION: {t['description']}
PARAMETERS: {json.dumps(t['parameters'], indent=2)}
"""

        msgs = [{"role": "system", "content": system_msg}] + messages

        response = ollama.chat(model=self.model, messages=msgs)
        return response
