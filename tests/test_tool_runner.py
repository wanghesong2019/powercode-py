from types import SimpleNamespace

import pytest

from powercode_py.context.recovery import RecoveryManager, ToolExecutionError
from powercode_py.tools.registry import Registry
from powercode_py.tools.tool_runner import run_tool_batch
from powercode_py.tools.types import ToolError


class _FakeTool:
    def __init__(self, name, result="ok", error=None):
        self.name = name
        self.definition = {"type": "function", "function": {"name": name}}
        self._result = result
        self._error = error

    def execute(self, arguments_json):
        if self._error is not None:
            raise self._error
        return self._result


def _call(tc_id, name, args):
    return SimpleNamespace(
        id=tc_id, type="function", function=SimpleNamespace(name=name, arguments=args)
    )


def test_run_tool_batch_success():
    registry = Registry()
    registry.register(_FakeTool("read_file", result="# 内容"))
    batch = run_tool_batch(
        [_call("1", "read_file", '{"path":"a.md"}')], registry, {"read_file"}, RecoveryManager()
    )
    assert batch["stop"] is False
    assert batch["messages"] == [{"role": "tool", "tool_call_id": "1", "content": "# 内容"}]


def test_run_tool_batch_failure_contains_hint():
    registry = Registry()
    registry.register(_FakeTool("edit_file", error=ToolError("没有找到 old_text")))
    batch = run_tool_batch(
        [_call("1", "edit_file", '{"path":"a.md"}')], registry, {"edit_file"}, RecoveryManager()
    )
    assert "工具执行失败" in batch["messages"][0]["content"]
    assert "[Harness 恢复提示]" in batch["messages"][0]["content"]
    assert batch["stop"] is False


def test_run_tool_batch_stop_skips_remaining():
    registry = Registry()
    registry.register(_FakeTool("bash", error=ToolExecutionError("permission", "越界")))
    registry.register(_FakeTool("read_file", result="ok"))
    batch = run_tool_batch(
        [
            _call("1", "bash", '{"command":"rm"}'),
            _call("2", "read_file", '{"path":"a"}'),
        ],
        registry,
        {"bash", "read_file"},
        RecoveryManager(),
    )
    assert batch["stop"] is True
    assert batch["messages"][1]["content"] == "本次运行已暂停，此工具调用未执行。"


def test_run_tool_batch_rejects_bad_type():
    registry = Registry()
    bad = SimpleNamespace(id="1", type="other", function=SimpleNamespace(name="x", arguments="{}"))
    with pytest.raises(ToolError, match="工具类型"):
        run_tool_batch([bad], registry, set(), RecoveryManager())
