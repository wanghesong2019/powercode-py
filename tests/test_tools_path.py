import pytest

from powercode_py.tools.path import ToolError, resolve_in_work_dir


def test_resolves_path_inside_workdir(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    assert resolve_in_work_dir(str(root), "src/a.py") == (root / "src" / "a.py").resolve()


def test_resolves_dotdot_inside_workdir(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    assert resolve_in_work_dir(str(root), "src/../a.py") == (root / "a.py").resolve()


def test_rejects_path_outside_workdir(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ToolError, match="只能操作当前项目里的文件"):
        resolve_in_work_dir(str(root), "../secret.txt")


def test_rejects_empty_path(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ToolError, match="不能为空"):
        resolve_in_work_dir(str(root), "   ")
