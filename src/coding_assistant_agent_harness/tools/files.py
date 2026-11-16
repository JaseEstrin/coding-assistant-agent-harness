from pathlib import Path

from .base import Tool, ToolError, resolve_in_project

MAX_LINES = 300
MAX_FILE_BYTES = 1_000_000 # refuse files bigger than 1 mb


def read_file(project_dir: Path, path: str, start_line: int = 1, end_line: int | None = None) -> str:
    file = resolve_in_project(project_dir, path)
    if not file.exists():
        raise ToolError(f"No such file: {path}")
    if file.is_dir():
        raise ToolError(f"{path} is a directory not a file")
    if file.stat().st_size > MAX_FILE_BYTES:
        raise ToolError(f"{path} is too large to read (over 1 mb)")

    data = file.read_bytes()
    if b"\0" in data[:8192]:
        raise ToolError(f"{path} looks like a binary file, not text")
    
    lines = data.decode("utf-8", errors="replace").splitlines()
    total = len(lines)
    shown_path = file.relative_to(project_dir.resolve())
    if total == 0:
        return f"{shown_path} is empty"

    start = max(1, start_line)
    if start > total:
        raise ToolError(f"start_line {start} is past the end of {path}, which has {total} lines")
    end = total if end_line is None else min(end_line, total)
    if end < start:
        raise ToolError("end_line must not be smaller than start_line")
    end = min(end, start + MAX_LINES - 1)

    width = len(str(end))
    body = "\n".join(f"{n:>{width}} | {lines[n - 1]}" for n in range(start, end + 1))
    result = f"{shown_path} (lines {start}-{end} of {total})\n{body}"
    if end < total:
        result += (
            f"\n[{total - end} more lines. "
            f"Call read_file with start_line={end + 1} to continue]"
        )
    return result


READ_FILE = Tool(
    name="read_file",
    description=(
        "Read a text file in the project. Lines are numbered. "
        "For long files, use start_line and end_line to read one part."
    ),
    parameters={
        "type": "object",
        "properties" : {
            "path": {"type": "string", "description": "File path, relative to the project root."},
            "start_line": {"type": "integer", "description": "First line to read (default 1)."},
            "end_line": {"type": "integer", "description": "Last line to read (default: end of file)."},
        },
        "required": ["path"]
    },
    function=read_file,
)