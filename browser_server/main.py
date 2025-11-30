from mcp.server.fastmcp import FastMCP 
from tools.tools import register_browser_tools

mcp = FastMCP("Browser")

def main():
    register_browser_tools(mcp)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
