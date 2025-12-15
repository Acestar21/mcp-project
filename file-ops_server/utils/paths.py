from pathlib import Path

def safe_join(root: Path, *parts) -> Path:
    """
    Securely joins paths and ensures the result is inside the root directory.
    Prevents directory traversal and sibling directory attacks.
    """
    # 1. Resolve the root to its absolute, canonical path
    root = root.resolve()
    
    # 2. Join and resolve the target path
    # (This handles '..' sequences automatically)
    new_path = (root / Path(*parts)).resolve()

    # 3. Security Check: is_relative_to
    # This checks if 'root' is a PARENT of 'new_path' in the filesystem tree.
    # It strictly enforces the boundary.
    try:
        new_path.relative_to(root)
    except ValueError:
        raise PermissionError(f"Security Violation: Access denied to '{new_path}' (Outside sandbox '{root}')")

    return new_path