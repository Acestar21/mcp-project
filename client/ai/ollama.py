import ollama
import json

class OllamaAI:
    def __init__(self, model="qwen2.5:latest"):
        self.model = model

    def generate(self, messages, tools):
        # 1. Base Instructions (The "Personality")
        system_rules = """
You are a helpful coding assistant. 

CORE RULES:
1. **Tool Usage**: 
    - If you need to perform an action (like creating files, writing code, reading dirs), you MUST use a tool.
    - Respond with ONE tool call at a time in this JSON format: {"tool": "<server>.<tool>", "args": { ... }}
    - Do NOT chain multiple tools in one message. Wait for the result before the next tool.
    - If a tool is called and the output is given YOU MUST ADHERE AND STICK WITH THE TOOL OUTPUT.
    - STATE ALL THE INFORMATION THAT YOU RECIEVED FROM TOOL OUTPUT.

2. **No Simulation**: 
    - Do NOT pretend to create or write files. You must actually call the tool.
    - If asked to write code to a file, use 'fileops.write_file'. Do not just show the code to the user.

3. **Natural Language**: 
    - If you are NOT using a tool, speak normally in Markdown.
    - Be concise.

4. **Tool Knowledge**: You have access to the following tools:
"""

        # 2. Add Tool Definitions dynamically
        for t in tools:
            system_rules += f"""
                - Name: {t['name']}
                    Description: {t['description']}
                    Parameters: {json.dumps(t['parameters'])}
        """

        # 3. Construct the Message List
        # We prefer to put the system instructions at the VERY START.
        # If the caller already provided a system message (like 'Summarize this'), we append ours or prepend.
        
        final_messages = [{"role": "system", "content": system_rules}]
        
        # Add the rest of the conversation history
        # (We skip existing system messages to avoid confusion, or you can keep them)
        for m in messages:
            if m["role"] != "system":
                final_messages.append(m)
            else:
                # If there was a specific system instruction (like the summarization prompt), add it as 'user' or 'system' secondary
                final_messages.append(m)

        # 4. Call Ollama
        try:
            response = ollama.chat(model=self.model, messages=final_messages , options={'temperature':0.0})

            return response
        except Exception as e:
            return {"message": {"content": f"Error: {str(e)}", "role": "assistant"}}