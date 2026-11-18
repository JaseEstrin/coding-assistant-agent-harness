from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class ToolError(Exception):
    """An expected problem (bad path, missing file, etc.) its message goes back to the model."""


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict # json schema
    function: Callable[..., str]
    needs_approval: bool = False

    @property
    def schema(self) -> dict:
        """The tool definition ollama expects"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def resolve_in_project(project_dir: Path, raw_path: str) -> Path:
    """Turn a path from the model into a real path. Refuse anything outside of the project"""
    root = project_dir.resolve()
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ToolError(f"'{raw_path}' is outside the project directory, so it can't be accessed.")
    return resolved