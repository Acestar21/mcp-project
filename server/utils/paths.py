from pathlib import Path

def safe_join(root: Path, *parts) -> Path:

    new_path = (root / Path(*parts)).resolve()

    if not str(new_path).startswith(str(root)):
        raise PermissionError("Access outside the sandbox is not allowed.")

    return new_path
