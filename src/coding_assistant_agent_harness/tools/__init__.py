import asyncio
from pathlib import Path

from .base import Tool, ToolError
from .files import READ_FILE

TOOLS: dict[str, Tool] = {tool.name: tool for tool in [READ_FILE]}


def tool_schemas() -> list[dict]:
    """All tool definitions, to send with every request"""
    return [tool.schema for tool in TOOLS.values()]


def _check_arguments(tool: Tool, arguments: dict) -> dict:
    """Check the mistakes small models make"""
    properties = tool.parameters.get("properties", {})
    missing = [name for name in tool.parameters.get("required", []) if name not in arguments]
    if missing:
        raise ToolError(f"Missing required argument(s) for {tool.name}: {', '.join(missing)}")
    unknown = [name for name in arguments if name not in properties]
    if unknown:
        raise ToolError(
            f"Unknown argument(s) for {tool.name}: {', '.join(unknown)}."
            f"Valid arguments: {', '.join(properties)}"
        )
    checked = {}
    for name, value in arguments.items():
        if properties[name].get("type") == "integer" and not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ToolError(f"Argument {name} must be a whole number, got {value!r}.") from None
        checked[name] = value
    return checked


async def run_tool(name: str, arguments: dict, project_dir: Path) -> str:
    """Run a tool and always return text. Errors become messages the model can act on"""
    tool = TOOLS.get(name)
    if tool is None:
        return f"Error: there is no tool called {name!r}. Available tools: {', '.join(TOOLS)}"
    try:
        checked = _check_arguments(tool, arguments)
        return await asyncio.to_thread(tool.function, project_dir, **checked)
    except ToolError as error:
        return f"Error: {error}"
    except Exception as error:  # noqa: BLE001
        return f"Error: {name} failed unexpectedly ({type(error).__name__}: {error})"