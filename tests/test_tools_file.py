import json

import pytest

from powercode_py.tools.edit_file import EditFileTool
from powercode_py.tools.read_file import ReadFileTool
from powercode_py.tools.types import ToolError
from powercode_py.tools.write_file import WriteFileTool


def _args(**kwargs):
    return json.dumps(kwargs)


def test_read_file_tool_reads(tmp_path):
    (tmp_path / "a.md").write_text("# 标题", encoding="utf-8")
    tool = ReadFileTool(work_dir=tmp_path)
    assert tool.execute(_args(path="a.md")) == "# 标题"


def test_read_file_tool_truncates(tmp_path):
    from powercode_py.tools.read_file import MAX_BYTES

    (tmp_path / "big.txt").write_text("x" * (MAX_BYTES + 100), encoding="utf-8")
    tool = ReadFileTool(work_dir=tmp_path)
    result = tool.execute(_args(path="big.txt"))
    assert result.startswith("x" * MAX_BYTES)
    assert "文件太长" in result


def test_read_file_tool_rejects_missing(tmp_path):
    tool = ReadFileTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="文件不存在"):
        tool.execute(_args(path="nope.md"))


def test_write_file_tool_creates_with_parent_dirs(tmp_path):
    tool = WriteFileTool(work_dir=tmp_path)
    result = tool.execute(_args(path="src/utils/a.py", content="print(1)"))
    assert (tmp_path / "src" / "utils" / "a.py").read_text(encoding="utf-8") == "print(1)"
    assert "已写入" in result


def test_write_file_tool_overwrites(tmp_path):
    (tmp_path / "a.py").write_text("old", encoding="utf-8")
    tool = WriteFileTool(work_dir=tmp_path)
    tool.execute(_args(path="a.py", content="new"))
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "new"


def test_edit_file_tool_replaces_unique_text(tmp_path):
    (tmp_path / "a.py").write_text("port = 3000\n", encoding="utf-8")
    tool = EditFileTool(work_dir=tmp_path)
    result = tool.execute(_args(path="a.py", old_text="3000", new_text="8080"))
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "port = 8080\n"
    assert "已修改" in result


def test_edit_file_tool_rejects_zero_match(tmp_path):
    (tmp_path / "a.py").write_text("hello", encoding="utf-8")
    tool = EditFileTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="没有找到"):
        tool.execute(_args(path="a.py", old_text="nope", new_text="x"))


def test_edit_file_tool_rejects_multiple_match(tmp_path):
    (tmp_path / "a.py").write_text("xx xx", encoding="utf-8")
    tool = EditFileTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="出现了 2 次"):
        tool.execute(_args(path="a.py", old_text="xx", new_text="y"))


def test_edit_file_tool_deletes_with_empty_new_text(tmp_path):
    (tmp_path / "a.py").write_text("keep this drop", encoding="utf-8")
    tool = EditFileTool(work_dir=tmp_path)
    tool.execute(_args(path="a.py", old_text=" drop", new_text=""))
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "keep this"
