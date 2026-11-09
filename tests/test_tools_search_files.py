import json

import pytest

from powercode_py.tools.search_files import SearchFilesTool
from powercode_py.tools.types import ToolError


def _args(query, path="."):
    return json.dumps({"query": query, "path": path})


def test_finds_keyword(tmp_path):
    (tmp_path / "a.py").write_text("print('hello')\nprint('world')\n")
    tool = SearchFilesTool(work_dir=tmp_path)
    result = tool.execute(_args("hello"))
    assert "a.py:1:" in result
    assert "hello" in result


def test_no_match(tmp_path):
    (tmp_path / "a.py").write_text("hello")
    tool = SearchFilesTool(work_dir=tmp_path)
    assert "没有找到关键词" in tool.execute(_args("zzz"))


def test_requires_query(tmp_path):
    tool = SearchFilesTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="query"):
        tool.execute(json.dumps({"path": "."}))
