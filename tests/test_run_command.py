import time

import pytest

from coding_assistant_agent_harness.tools import needs_approval
from coding_assistant_agent_harness.tools.base import ToolError
from coding_assistant_agent_harness.tools.commands import MAX_OUTPUT_LINES, run_command


def test_run_command_requires_approval():
    assert needs_approval("run_command")
    assert not needs_approval("read_file")


def test_shows_output_and_success(tmp_path):
    result = run_command(tmp_path, "echo hello")
    assert "Exit code 0 (success)" in result and "hello" in result


def test_reports_failure_and_stderr(tmp_path):
    result = run_command(tmp_path, "echo oops >&2; exit 3")
    assert "Exit code 3 (failed)" in result and "oops" in result


def test_runs_in_project_folder(tmp_path):
    (tmp_path / "marker.txt").write_text("x")
    assert "marker.txt" in run_command(tmp_path, "ls")


def test_command_waiting_for_input_does_not_hang(tmp_path):
    start = time.monotonic()
    run_command(tmp_path, "read answer; echo got:$answer", timeout_seconds=5)
    assert time.monotonic() - start < 3


def test_timeout_stops_the_command(tmp_path):
    start = time.monotonic()
    result = run_command(tmp_path, "sleep 30", timeout_seconds=1)
    assert "Timed out after 1s" in result
    assert time.monotonic() - start < 5


def test_long_output_keeps_the_end(tmp_path):
    result = run_command(tmp_path, f"seq 1 {MAX_OUTPUT_LINES + 50}")
    assert "[50 earlier lines not shown]" in result
    assert str(MAX_OUTPUT_LINES + 50) in result


def test_empty_command_is_refused(tmp_path):
    with pytest.raises(ToolError):
        run_command(tmp_path, "  ")