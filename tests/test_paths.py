import pytest

from coding_assistant_agent_harness.tools.base import ToolError, resolve_in_project


def test_relative_path_inside_project(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    assert resolve_in_project(tmp_path, "main.py") == (tmp_path / "main.py").resolve()


def test_dot_dot_escape_is_refused(tmp_path):
    with pytest.raises(ToolError):
        resolve_in_project(tmp_path, "../outside.txt")


def test_sneaky_dot_dot_is_refused(tmp_path):
    (tmp_path / "src").mkdir()
    with pytest.raises(ToolError):
        resolve_in_project(tmp_path, "src/../../outside.txt")


def test_absolute_path_outside_is_refused(tmp_path):
    with pytest.raises(ToolError):
        resolve_in_project(tmp_path, "/etc/passwd")


def test_home_shortcut_outside_is_refused(tmp_path):
    with pytest.raises(ToolError):
        resolve_in_project(tmp_path, "~/.bashrc")


def test_symlink_pointing_outside_is_refused(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("private")
    (project / "link.txt").symlink_to(secret)
    with pytest.raises(ToolError):
        resolve_in_project(project, "link.txt")