import os
import signal
import subprocess
from pathlib import Path

from .base import Tool, ToolError

DEFAULT_TIMEOUT_SECONDS = 120
MAX_OUTPUT_LINES = 200 # keep the end of long output


def _kill_process_group(process: subprocess.Popen) -> None:
    """Stop the shell nd everything it started"""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_command(project_dir: Path, command: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    if not command.strip():
        raise ToolError("command must not be empty.")

    process = subprocess.Popen(
        command,
        shell=True, # allows pipes, &&, and commands to work
        cwd=project_dir,
        stdin=subprocess.DEVNULL, # a command that asks for input gets none instead of hanging
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # one stream so errors appear in order
        text=True,
        errors="replace",
        start_new_session=True, # its own process group so everything can be stopped with timeout
    )
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        output, _ = process.communicate()
        timed_out = True

    lines = (output or "").splitlines()
    note = ""
    if len(lines) > MAX_OUTPUT_LINES:
        note = f"[{len(lines) - MAX_OUTPUT_LINES} earlier lines not shown]\n"
        lines = lines[-MAX_OUTPUT_LINES:]
    body = note + "\n".join(lines) if lines else "(no output)"

    if timed_out:
        status = f"Timed out after {timeout_seconds}s and was stopped."
    else:
        status = f"Exit code {process.returncode}" + (" (success)" if process.returncode == 0 else " (failed)")
    return f"$ {command}\n{status}\n{body}"


RUN_COMMAND = Tool(
    name="run_command",
    description=(
        "Run a shell command in the project folder, such as tests, a linter, or a formatter "
        "(for example: uv run pytest -q). The user must approve every command before it runs. "
        f"Commands are stopped after {DEFAULT_TIMEOUT_SECONDS} seconds."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The exact shell command to run."},
        },
        "required": ["command"],
    },
    function=run_command,
    needs_approval=True,
)