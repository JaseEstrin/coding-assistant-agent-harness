import os
from collections.abc import Iterator
from pathlib import Path

from .base import Tool, ToolError, resolve_in_project
from .directories import IGNORED_NAMES

MAX_MATCHES = 50 # matching lines returned every call
MAX_NAME_MATCHES = 20 # matching file paths returned every call
MAX_FILE_BYTES = 1_000_000 # skip files bigger than 1 mb
MAX_LINE_CHARS = 200 # long lines get cut short


def _iter_files(start: Path) -> Iterator[Path]:
    """Every searchable file under start in order, skipping noise folders"""
    if start.is_file():
        yield start
        return
    for dirpath, dirnames, filenames in os.walk(start):
        # editing dirnames tells os.walk not to go into these folders
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_NAMES)
        for name in sorted(filenames):
            file = Path(dirpath) / name
            if not file.is_symlink():
                yield file


def _shorten(line: str) -> str:
    line = line.strip()
    return line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + "..."


def search_files(project_dir: Path, query: str, path: str = ".", case_sensitive: bool = False) -> str:
    if not query.strip():
        raise ToolError("query must not be empty")
    start = resolve_in_project(project_dir, path)
    if not start.exists():
        raise ToolError(f"No such file or directory: {path}")

    root = project_dir.resolve()
    needle = query if case_sensitive else query.lower()

    def contains(text: str) -> bool:
        return needle in (text if case_sensitive else text.lower())

    name_matches: list[str] = []
    line_matches: list[str] = []
    total_lines = 0
    files_with_matches = 0

    for file in _iter_files(start):
        relative = str(file.relative_to(root))
        if contains(relative) and len(name_matches) < MAX_NAME_MATCHES:
            name_matches.append(relative)

        try:
            if file.stat().st_size > MAX_FILE_BYTES:
                continue
            data = file.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue

        found_here = False
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), start=1):
            if contains(line):
                total_lines += 1
                found_here = True
                if len(line_matches) < MAX_MATCHES:
                    line_matches.append(f"{relative}:{number}: {_shorten(line)}")
        if found_here:
            files_with_matches += 1
    
    mode = "case-sensitive" if case_sensitive else "case-insensitive"
    header = f'Search for "{query}" ({mode})'
    if not name_matches and not line_matches:
        return f"{header}\nNo matches found."

    parts = [header]
    if name_matches:
        parts.append("Files whose path contains the text:\n" + "\n".join(name_matches))
    if line_matches:
        summary = f"[{total_lines} matching lines in {files_with_matches} files]"
        parts.append("Matching lines (path:line: text):\n" + "\n".join(line_matches) + "\n" + summary)
        if total_lines > MAX_MATCHES:
            parts.append(
                f"[Showing the first {MAX_MATCHES}. Use a more specific query, "
                "or set path to search one folder or file.]"
            )
    return "\n\n.".join(parts)


SEARCH_FILES = Tool(
    name="search_files",
    description=(
        "Search the project's files for exact text (not a regular expression). "
        "Returns matching lines as path:line: text, and files whose path contains the text. "
        "Then use read_file with start_line to read around a match."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The text to search for."},
            "path": {
                "type": "string",
                "desription": "Folder or file to search , relative to the project root (default: the whole project).",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Match upper and lower case exactly (default false).",
            },
        },
        "required": ["query"],
    },
    function=search_files,
)