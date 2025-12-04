import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient()
    try:
        await client.connect_all()

        # Example: call fileops list_directory
        print("\n--- Testing tool call ---")
        raw = await client.call_tool("fileops", "read_file", {"path": "D:\\Programming\\Projects\\mcp-project\\file-ops_server\\sandbox\\images\\multiply.py\\multiply.py"})
        print("RAW:", raw)
        print("TEXT:\n", MCPClient.print_response(raw))

    finally:
        await client.cleanup()
if __name__ == "__main__":
    asyncio.run(main())