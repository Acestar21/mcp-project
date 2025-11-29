from mcp.server.fastmcp import FastMCP
from pathlib import Path

from tools.file_ops import register_file_tools

SANDBOX_DIR = Path(__file__).parent.parent / "sandbox"
SANDBOX_DIR = SANDBOX_DIR.resolve()

mcp = FastMCP("File-Operations")

def main():
    register_file_tools(mcp, SANDBOX_DIR)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()  