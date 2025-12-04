import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient()
    try:
        await client.connect_all()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
