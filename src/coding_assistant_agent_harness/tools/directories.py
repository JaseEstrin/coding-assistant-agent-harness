from pathlib import Path

from .base import Tool, ToolError, resolve_in_project

MAX_DEPTH = 4
MAX_ENTRIES = 200

IGNORED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size = size_bytes / 1024
    for unit in ("KB", "MB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def list_directory(project_dir: Path, path: str = ".", depth: int = 1) -> str:
    folder = resolve_in_project(project_dir, path)
    if not folder.exists():
        raise ToolError(f"No such directory: {path}")
    if not folder.is_dir():
        raise ToolError(f"{path} is a file, not a directory. use read_file to read it")
    
    depth = max(1, min(depth, MAX_DEPTH))
    root = project_dir.resolve()
    lines: list[str] = []
    skipped: set[str] = set()
    truncated = False

    def walk(directory: Path, level: int) -> None:
        nonlocal truncated
        try:
            # folders first, then files. all alphabetical
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            lines.append(f"{' ' * level}(permission denied)")
            return
        
        for entry in entries:
            if entry.name in IGNORED_NAMES:
                skipped.add(entry.name)
                continue
            if len(lines) >= MAX_ENTRIES:
                truncated = True
                return

            indent = " " * level
            if entry.is_symlink():
                # show links but don't follow
                lines.append(f"{indent}{entry.name}@  (symlink)")
            elif entry.is_dir():
                lines.append(f"{indent}{entry.name}/")
                if level + 1 < depth:
                    walk(entry, level + 1)
            else:
                try:
                    size = _format_size(entry.stat().st_size)
                except OSError:
                    size = "size unknown"
                lines.append(f"{indent}{entry.name}  ({size})")

            if truncated:
                return
    
    walk(folder, 0)

    shown_path = "." if folder == root else str(folder.relative_to(root))
    header = f"{shown_path}/ (depth {depth})"
    if not lines:
        return f"{header}\n(empty)"

    result = header + "\n" + "\n".join(lines)
    if truncated:
        result += (
            f"\n[Stopped at {MAX_ENTRIES} entries. "
            "List a subfolder, or use a smaller depth.]"
        )
    if skipped:
        result += f"\n[Not shown: {','.join(sorted(skipped))}]"
    return result


LIST_DIRECTORY = Tool(
    name="list_directory",
    description=(
        "List the files and folders in a project directory. Folders end with '/'."
        "Use depth 2 or 3 to see the project's layout in one call."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path, relative to the project root (default: the root).",
            },
            "depth": {
                "type": "integer",
                "description": f"How many levels of subfolders to include, 1 to {MAX_DEPTH} (default 1).",
            },
        },
        "required": [],
    },
    function=list_directory
)