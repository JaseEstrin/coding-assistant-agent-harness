import pytest

from coding_assistant_agent_harness.tools.base import ToolError
from coding_assistant_agent_harness.tools.search import MAX_MATCHES, search_files


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "agent.py").write_text("import os\n\ndef load_system_prompt():\n    pass\n")
    (tmp_path / "src" / "config.py").write_text("MODEL_NAME = 'qwen'\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("def load_system_prompt(): ...\n")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\0\0load_system_prompt")
    return tmp_path


def test_finds_line_with_path_and_number(project):
    result = search_files(project, "load_system_prompt")
    assert "src/agent.py:3: def load_system_prompt():" in result


def test_case_insensitive_by_default(project):
    assert "src/config.py:1:" in search_files(project, "model_name")


def test_case_sensitive_option(project):
    assert "No matches found." in search_files(project, "model_name", case_sensitive=True)


def test_skips_noise_folders_and_binary_files(project):
    result = search_files(project, "load_system_prompt")
    assert ".venv" not in result and "image.png" not in result


def test_matches_file_paths(project):
    assert "src/config.py" in search_files(project, "config.py")


def test_limited_to_a_subfolder(project):
    (project / "README.md").write_text("load_system_prompt is documented here\n")
    result = search_files(project, "load_system_prompt", path="src")
    assert "README.md" not in result and "src/agent.py:3:" in result


def test_caps_number_of_matches(project):
    (project / "many.txt").write_text("needle\n" * (MAX_MATCHES + 25))
    result = search_files(project, "needle")
    assert f"[{MAX_MATCHES + 25} matching lines in 1 files]" in result
    assert f"Showing the first {MAX_MATCHES}" in result


def test_outside_project_is_refused(project):
    with pytest.raises(ToolError):
        search_files(project, "root", path="..")


def test_empty_query_is_refused(project):
    with pytest.raises(ToolError):
        search_files(project, "  ")