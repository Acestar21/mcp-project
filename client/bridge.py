import asyncio
import json
import sys
import traceback
from mcp_client import MCPClient

def send_json(obj):
    print(json.dumps(obj, ensure_ascii=True),flush=True)
    sys.stdout.flush()

async def run_bridge():
    client = MCPClient()

    def handle_event(event :dict):
        send_json(event)
    # bridge.py

    print("READY", flush=True)

    try:    
        await client.connect_all(event_handler=handle_event)

    except Exception as e:
        send_json({
            "error": "Failed to connect to MCP servers",
            "message": str(e),
            "trace" : traceback.format_exc()
        })
        return 1
    
    send_json({"status": "connected"})


    while True:
        line = sys.stdin.readline()
        if not line:
            break 

        line = line.strip()
        if not line:
            continue

        try :
            data =  json.loads(line)
        
        except Exception as e:
            send_json({
                "error": "Invalid JSON input",
                "message": str(e),
                "raw": line
            })
            continue

        if data.get("cmd") == "__shutdown__":
            break

        query = data.get("query")

        if query is None:
            send_json({
                "error": "No query provided",
                "message": "Each command must include a 'query' field"
            })
            continue

        try :
            result = await client.process(query, event_handler=handle_event)
            if isinstance(result, (dict, list)):
                send_json({"type": "response", "ok": True, "response": result})
            else:
                send_json({"type": "response", "ok": True, "response": str(result)})
        except Exception as e:
            send_json({"ok": False, "error": str(e), "trace": traceback.format_exc()})



    try : 
        await client.cleanup()

    except Exception:
        pass
        
    
    return 0

if __name__ == "__main__":
    asyncio.run(run_bridge())