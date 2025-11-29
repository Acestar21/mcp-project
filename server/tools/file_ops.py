from mcp.server.fastmcp import FastMCP
from pathlib import Path
from utils.paths import safe_join

SANDBOX = None

def register_file_tools(mcp: FastMCP, sandbox_root: Path):

    global SANDBOX
    SANDBOX = sandbox_root


    pass
