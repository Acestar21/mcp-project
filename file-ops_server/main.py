from mcp.server.fastmcp import FastMCP
from pathlib import Path

from tools.file_ops import register_file_tools

SANDBOX_DIR = Path(__file__).parent / "sandbox"
SANDBOX_DIR = SANDBOX_DIR.resolve()
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
# Ensure the sandbox directory exists for experimenting with file operations in current directory 

mcp = FastMCP("File-Operations")

def main():
    register_file_tools(mcp, SANDBOX_DIR)
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()  