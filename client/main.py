import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient()

    try:
        await client.connect_all()

        print("\nMCP Assistant Ready! Type 'quit' to exit.\n")
        tol = await client.get_all_tools()

        while True:
            query = input("You: ").strip()
            if query.lower() == "quit":
                break

            answer = await client.process(query)
            print("\nAssistant:", answer, "\n")

    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
