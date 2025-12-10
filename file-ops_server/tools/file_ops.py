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
        
    @mcp.tool() # Rename File Tool
    async def rename_file(old_path:str , new_path:str) ->str:
        """
        Rename a file or directory inside the sandbox.

        Args:
            old_path: Current path of the file or directory.
            new_path: New desired path.
        """
        old_path_target = safe_join(SANDBOX, old_path)
        new_path_target = safe_join(SANDBOX, new_path)

        if not old_path_target.exists():
            return f"Error: '{old_path}' does not exist."
        if new_path_target.exists() and new_path_target.is_dir():
            return f"Error: Cannot overwrite an existing directory: {new_path}"
        
        try:
            new_path_target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"Error creating parent directories: {str(e)}"
        
        try :
            old_path_target.rename(new_path_target)
            return f"Successfully renamed '{old_path}' to '{new_path}'."
        except Exception as e:
            return f"Error renaming file or directory: {str(e)}"
        
    @mcp.tool() # Move Tool
    async def move_file(source_path: str, dest_path: str) -> str:
        """
        Move a file or directory within the sandbox.
        
        - If dest_path is an existing directory (or ends with '/'), moves source into it.
        - Otherwise, moves/renames source to dest_path.
        """
        source = safe_join(SANDBOX, source_path)
        dest = safe_join(SANDBOX, dest_path)

        if not source.exists():
            return f"Error: Source '{source_path}' does not exist."

        # Determine if the user intends to move INTO a directory
        # 1. It ends with a slash (explicit directory intention)
        # 2. It matches an existing directory
        is_directory_move = dest_path.endswith('/') or dest_path.endswith('\\') or (dest.exists() and dest.is_dir())

        if is_directory_move:
            # Move INTO the directory
            try:
                dest.mkdir(parents=True, exist_ok=True)
                target = dest / source.name
                
                if target.exists():
                    return f"Error: '{target.name}' already exists in '{dest_path}'."
                
                source.rename(target)
                return f"Successfully moved '{source_path}' into '{dest_path}'."
            except Exception as e:
                return f"Error moving file: {str(e)}"
        
        else:
            # Move TO the specific path (Rename)
            if dest.exists():
                return f"Error: Destination '{dest_path}' already exists."
            
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                source.rename(dest)
                return f"Successfully moved/renamed '{source_path}' to '{dest_path}'."
            except Exception as e:
                return f"Error moving file: {str(e)}"

    @mcp.tool() # file info tool
    async def file_info(path: str) -> dict:
        """
        Get detailed information about a file or directory inside the sandbox.

        Args:
            path: Target file or folder path.
        """
        target = safe_join(SANDBOX, path)
        
        if not target.exists():
            return {"error":f"'{path}' does not exist. "}
        
        try:
            stat = target.stat()
            info = {
                "name" : target.name,
                "path" : path,
                "absolute_path": str(target),
                "type" : "directory" if target.is_dir() else "file",

                "size_bytes" : stat.st_size if target.is_file() else None,

                "created_at" : stat.st_ctime,
                "modified_at" : stat.st_mtime,
                "accessed_at" : stat.st_atime,

                "is_empty_directory": (
                    target.is_dir() and not any(target.iterdir())
                ),
            }

            return info
        
        except Exception as e:
            return {"error": f"Error retrieving file info: {str(e)}"}
        
    @mcp.tool() # Search Files Tool
    async def search_files(query: str) -> list[str]:
        """
        Search for files or directories whose names contain the query string.
        The search is recursive inside the sandbox.

        Args:
            query: The substring to search for (case-insensitive).
        """

        query = query.lower()
        matches = []

        for path in SANDBOX.rglob('*'):
            if query in path.name.lower():
                relative_path = path.relative_to(SANDBOX)
                matches.append(str(relative_path))

        return matches
    
    @mcp.tool()
    async def create_directory(path: str) -> str:
        """
        Create a directory (including parents) inside the sandbox.

        Args:
            path: Directory path to create.
        """

        target = safe_join(SANDBOX, path)

        if target.exists():
            if target.is_dir():
                return f"Directory '{path}' already exists."
            else:
                return f"Error: A file with the name '{path}' already exists."


        try:
            target.mkdir(parents=True, exist_ok=True)
            return f"Created directory '{path}'."
        except Exception as e:
            return f"Error creating directory: {str(e)}"
