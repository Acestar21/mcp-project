from mcp.server.fastmcp import FastMCP
from pathlib import Path
from utils.paths import safe_join

SANDBOX = None

def register_file_tools(mcp: FastMCP, sandbox_root: Path):

    global SANDBOX
    SANDBOX = sandbox_root
    # register module-level tools with the provided mcp instance
    

    @mcp.tool() # List Directory Tool
    async def list_directory(path: str) -> list[str]:
        """List files and directories in the given path within the sandbox."""
        
        target = safe_join(SANDBOX, path)
        if not target.exists():
            raise FileNotFoundError(f"Path '{path}' does not exist.")
        if not target.is_dir():
            raise NotADirectoryError(f"Path '{path}' is not a directory.")
        
        items = []
        for entry in target.iterdir():
            if entry.is_dir():
                items.append(entry.name+'/')
                
            else:
                items.append(entry.name)
        return items
    
    @mcp.tool() # Read File Tool
    async def read_file(path: str) -> str:
        """
        Read the contents of a file at the given path within the sandbox.
        """
        target = safe_join(SANDBOX, path)
        if not target.exists():
            raise FileNotFoundError(f"File '{path}' does not exist.")
        if not target.is_file():
            raise IsADirectoryError(f"Path '{path}' is not a file.")
        
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "Error: File is not a UTF-8 text file."
        except Exception as e:
            return f"Error reading file: {str(e)}"
        
    @mcp.tool() # Write File Tool
    async def write_file(path: str, content: str) -> str:
        """
        Write content to a file at the given path within the sandbox.
        Creates the file if it does not exist.
        """
        target = safe_join(SANDBOX, path)
        if target.exists() and target.is_dir():
            raise IsADirectoryError(f"Path '{path}' is a directory.")
        
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Successfully wrote to file '{path}'."
        except Exception as e:
            return f"Error writing to file: {str(e)}"
        
    @mcp.tool() # Create File Tool
    async def create_file(path: str) -> str:
        """
        Create an empty file at the given path inside the sandbox.

        Args:
            path: Relative file path to create.
        """
        target = safe_join(SANDBOX, path)
        if target.exists() and target.is_file():
            raise FileExistsError(f"File '{path}' already exists.")
        
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            return f"Successfully created file '{path}'."
        except Exception as e:
            return f"Error creating file: {str(e)}"
        
    @mcp.tool() # Delete File Tool
    async def delete_file(path: str) -> str:
        """
        Delete a file or empty directory inside the sandbox.

        Args:
            path: Path of the file or directory to delete.
        """
        target = safe_join(SANDBOX, path)
        if not target.exists():
            return f"Error: '{path}' does not exist."
        
        if target.is_dir():
            try:
                target.rmdir()   # rmdir only deletes EMPTY dirs
                return f"Directory deleted: {path}"
            except OSError:
                return f"Error: Directory '{path}' is not empty."
            except Exception as e:
                return f"Error deleting directory: {str(e)}"
        
        try:
            target.unlink()
            return f"File deleted: {path}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"