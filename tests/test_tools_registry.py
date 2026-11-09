import pytest

from powercode_py.tools.registry import Registry
from powercode_py.tools.types import ToolError


class _FakeTool:
    def __init__(self, name, definition=None, result="ok"):
        self.name = name
        self.definition = definition or {
            "type": "function",
            "function": {"name": name},
        }
        self.result = result

    def execute(self, arguments_json):
        return self.result


def test_register_and_get_definitions():
    r = Registry()
    t1 = _FakeTool("read_file")
    t2 = _FakeTool("bash")
    r.register(t1)
    r.register(t2)
    assert r.get_definitions() == [t1.definition, t2.definition]


def test_duplicate_register_raises():
    r = Registry()
    r.register(_FakeTool("read_file"))
    with pytest.raises(ToolError, match="重复注册"):
        r.register(_FakeTool("read_file"))


def test_execute_found_tool():
    r = Registry()
    r.register(_FakeTool("read_file", result="内容"))
    assert r.execute("read_file", '{"path":"a.md"}') == "内容"


def test_execute_unknown_tool_raises():
    r = Registry()
    with pytest.raises(ToolError, match="找不到工具"):
        r.execute("nope", "{}")


def test_get_definitions_filters_by_allowed():
    r = Registry()
    r.register(_FakeTool("read_file"))
    r.register(_FakeTool("write_file"))
    assert r.get_definitions({"read_file"}) == [
        {"type": "function", "function": {"name": "read_file"}}
    ]


def test_execute_rejects_disallowed():
    r = Registry()
    r.register(_FakeTool("write_file"))
    with pytest.raises(ToolError, match="不允许调用"):
        r.execute("write_file", "{}", {"read_file"})
