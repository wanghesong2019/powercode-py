from powercode_py.context.recovery import (
    RecoveryManager,
    ToolExecutionError,
    call_key,
    classify_failure,
)
from powercode_py.tools.types import ToolError


def test_classify_edit_mismatch():
    assert (
        classify_failure("edit_file", ToolError("没有找到 old_text，请重新读取文件后再试。"))
        == "edit_mismatch"
    )


def test_classify_edit_ambiguous():
    assert classify_failure("edit_file", ToolError("old_text 出现了 2 次")) == "edit_ambiguous"


def test_classify_not_found():
    assert classify_failure("read_file", ToolError("文件不存在：x")) == "not_found"


def test_classify_permission():
    assert classify_failure("bash", ToolError("只能操作当前项目里的文件。")) == "permission"


def test_classify_tool_execution_error_kind():
    assert classify_failure("bash", ToolExecutionError("timeout", "超时")) == "timeout"
    assert classify_failure("bash", ToolExecutionError("command_failed", "失败")) == "command_failed"


def test_classify_unknown():
    assert classify_failure("bash", ToolError("奇怪错误")) == "unknown"


def test_call_key_ignores_key_order():
    assert call_key("edit_file", '{"b": 1, "a": 2}') == call_key("edit_file", '{"a": 2, "b": 1}')


def test_call_key_differs_by_args():
    assert call_key("edit_file", '{"a": 1}') != call_key("edit_file", '{"a": 2}')


def test_recovery_manager_stop_after_3_same():
    rm = RecoveryManager()
    err = ToolExecutionError("command_failed", "失败")
    d1 = rm.on_failure("bash", '{"command":"x"}', err)
    d2 = rm.on_failure("bash", '{"command":"x"}', err)
    d3 = rm.on_failure("bash", '{"command":"x"}', err)
    assert (d1.stop, d2.stop, d3.stop) == (False, False, True)
    assert d3.count == 3


def test_recovery_manager_success_clears_call_count():
    rm = RecoveryManager()
    err = ToolExecutionError("command_failed", "失败")
    rm.on_failure("bash", '{"command":"x"}', err)
    rm.on_failure("bash", '{"command":"x"}', err)
    rm.on_success("bash", '{"command":"x"}')
    d = rm.on_failure("bash", '{"command":"x"}', err)
    assert d.count == 1


def test_recovery_manager_stop_on_permission():
    rm = RecoveryManager()
    d = rm.on_failure("write_file", "{}", ToolExecutionError("permission", "越界"))
    assert d.stop is True


def test_recovery_manager_output_contains_hint():
    rm = RecoveryManager()
    d = rm.on_failure("edit_file", '{"path":"a"}', ToolError("没有找到 old_text"))
    assert "[Harness 恢复提示]" in d.output
    assert "edit_mismatch" in d.output
