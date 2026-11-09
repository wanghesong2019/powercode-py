import json

from powercode_py.tools.list_files import ListFilesTool


def _args(path="."):
    return json.dumps({"path": path})


def test_lists_files_and_dirs(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    tool = ListFilesTool(work_dir=tmp_path)
    result = tool.execute(_args())
    assert "a.txt" in result
    assert "sub/" in result
    assert "sub/b.txt" in result


def test_skips_git_directory(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "x.txt").write_text("x")
    tool = ListFilesTool(work_dir=tmp_path)
    result = tool.execute(_args())
    assert ".git" not in result
    assert "x.txt" in result


def test_empty_directory(tmp_path):
    tool = ListFilesTool(work_dir=tmp_path)
    assert tool.execute(_args()) == "目录为空。"
