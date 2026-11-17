import pytest

from coding_assistant_agent_harness.tools.base import ToolError
from coding_assistant_agent_harness.tools.directories import list_directory


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "main.py").write_text("print('hi')")
    (tmp_path / "README.md").write_text("# readme")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    return tmp_path


def test_depth_one_shoes_only_top_level(project):
    result = list_directory(project)
    assert "src/" in result and "README.md" in result
    assert "pkg/" not in result


def test_depth_three_shows_nested_files(project):
    result = list_directory(project, depth=3)
    assert "pkg/" in result and "main.py" in result


def test_noise_folders_are_hidden_but_mentioned(project):
    result = list_directory(project, depth=3)
    assert "lib" not in result
    assert "[Not shown: .venv]" in result


def test_folders_come_before_files(project):
    result = list_directory(project)
    assert result.index("src/") < result.index("README.md")


def test_outside_project_is_refused(project):
    with pytest.raises(ToolError):
        list_directory(project, "..")


def test_file_path_gives_helpful_error(project):
    with pytest.raises(ToolError, match="read_file"):
        list_directory(project, "README.md")


def test_symlinked_folder_is_not_followed(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("private")
    (project / "link").symlink_to(outside)
    result = list_directory(project, depth=3)
    assert "link@" in result and "secret.txt" not in result