import json

import pytest

from powercode_py.read_file import MAX_BYTES, ReadFileError, read_file_tool


def _args(path):
    return json.dumps({"path": path})


def test_reads_file_in_workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# 你好", encoding="utf-8")

    assert read_file_tool(_args("README.md")) == "# 你好"


def test_truncates_file_over_max_bytes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "big.txt").write_text("x" * (MAX_BYTES + 100), encoding="utf-8")

    result = read_file_tool(_args("big.txt"))

    assert result.startswith("x" * MAX_BYTES)
    assert "文件太长了" in result


def test_rejects_path_outside_workdir(tmp_path, monkeypatch):
    (tmp_path / "sub").mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.chdir(tmp_path / "sub")

    with pytest.raises(ReadFileError, match="只能读取当前项目里的文件"):
        read_file_tool(_args("../secret.txt"))


def test_rejects_missing_path_argument():
    with pytest.raises(ReadFileError, match="文件路径"):
        read_file_tool(json.dumps({"foo": "bar"}))


def test_rejects_non_string_path():
    with pytest.raises(ReadFileError, match="文件路径"):
        read_file_tool(json.dumps({"path": 123}))


def test_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ReadFileError, match="文件不存在"):
        read_file_tool(_args("nope.txt"))


def test_rejects_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "subdir").mkdir()
    with pytest.raises(ReadFileError, match="目录"):
        read_file_tool(_args("subdir"))
