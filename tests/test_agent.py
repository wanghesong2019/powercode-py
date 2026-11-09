import json
from types import SimpleNamespace

import pytest

from powercode_py import agent
from powercode_py.agent import Agent, AgentError
from powercode_py.context.session import Session
from powercode_py.plan import AgentState
from powercode_py.tools.registry import Registry
from powercode_py.tools.submit_plan import SubmitPlanTool
from powercode_py.tools.types import ToolError
from powercode_py.context.recovery import ToolExecutionError


def _assistant(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(name="read_file", arguments='{"path":"README.md"}', tc_id="call_1"):
    return SimpleNamespace(
        id=tc_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class _FakeTool:
    def __init__(self, name, definition=None, result="ok", error=None):
        self.name = name
        self.definition = definition or {"type": "function", "function": {"name": name}}
        self._result = result
        self._error = error

    def execute(self, arguments_json):
        if self._error is not None:
            raise self._error
        return self._result


class _Result:
    def __init__(self, message, total_tokens):
        self.message = message
        self.total_tokens = total_tokens


class ScriptedClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get_context_window(self):
        return 128000

    def complete_with_usage(self, messages, tools):
        self.calls.append((messages, tools))
        if not self._responses:
            raise AssertionError("脚本化的响应用完了")
        return _Result(self._responses.pop(0), 1000)


def _registry(tool):
    r = Registry()
    r.register(tool)
    return r


def _agent(client, registry, state=None):
    return Agent(client, registry, Session(), state or AgentState())


def test_run_returns_answer_when_no_tool_call():
    client = ScriptedClient([_assistant(content="直接回答")])
    a = _agent(client, Registry())
    assert a.run("你好") == "直接回答"


def test_run_tool_then_answer():
    reg = _registry(_FakeTool("read_file", result="# 内容"))
    reg.register(_FakeTool("write_file"))
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call()]),
            _assistant(content="这是答案"),
        ]
    )
    a = _agent(client, reg)
    result = a.run("这个项目是做什么的？")
    assert result == "这是答案"
    msgs = client.calls[1][0]
    assert msgs[0] == {"role": "system", "content": agent.CORE_SYSTEM_PROMPT}
    assert msgs[1] == {"role": "user", "content": "这个项目是做什么的？"}
    assert msgs[2]["role"] == "assistant"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": "# 内容"}
    names = [d["function"]["name"] for d in client.calls[0][1]]
    assert "write_file" in names


def test_run_plan_mode_restricts_tools():
    reg = _registry(_FakeTool("read_file", result="# 内容"))
    reg.register(_FakeTool("write_file"))
    client = ScriptedClient([_assistant(content="直接回答")])
    a = _agent(client, reg, AgentState("plan"))
    a.run("规划一下")
    names = [d["function"]["name"] for d in client.calls[0][1]]
    assert "read_file" in names
    assert "write_file" not in names


def test_run_submit_plan_pauses_loop():
    state = AgentState("plan")
    registry = Registry()
    registry.register(SubmitPlanTool(state))
    submit_call = _tool_call(
        name="submit_plan",
        arguments=json.dumps(
            {"title": "重构登录", "content": "## 目标\n重构", "steps": ["找到入口"]}
        ),
    )
    client = ScriptedClient([_assistant(content=None, tool_calls=[submit_call])])
    a = _agent(client, registry, state)
    result = a.run("帮我规划重构登录")
    assert result.startswith("# 重构登录")
    assert state.get_status() == "waiting_for_approval"
    assert len(client.calls) == 1


def test_run_handles_multiple_tool_calls_in_one_round():
    reg = _registry(_FakeTool("read_file", result="内容"))
    client = ScriptedClient(
        [
            _assistant(
                content=None,
                tool_calls=[
                    _tool_call(arguments='{"path":"a.md"}', tc_id="c1"),
                    _tool_call(arguments='{"path":"b.md"}', tc_id="c2"),
                ],
            ),
            _assistant(content="读完了"),
        ]
    )
    a = _agent(client, reg)
    result = a.run("读两个文件")
    assert result == "读完了"
    msgs = client.calls[1][0]
    assert msgs[3] == {"role": "tool", "tool_call_id": "c1", "content": "内容"}
    assert msgs[4] == {"role": "tool", "tool_call_id": "c2", "content": "内容"}


def test_run_feeds_back_tool_failure():
    reg = _registry(_FakeTool("read_file", error=ToolError("文件不存在")))
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call()]),
            _assistant(content="文件找不到"),
        ]
    )
    a = _agent(client, reg)
    result = a.run("读个不存在的文件")
    assert result == "文件找不到"
    msgs = client.calls[1][0]
    assert msgs[3]["role"] == "tool"
    assert msgs[3]["content"].startswith("工具执行失败")


def test_run_stops_on_disallowed_tool():
    client = ScriptedClient(
        [_assistant(content=None, tool_calls=[_tool_call(name="nope")])]
    )
    a = _agent(client, Registry())
    result = a.run("hi")
    assert result.startswith("本次运行已暂停")
    assert "不允许调用" in result
    assert len(client.calls) == 1


def test_run_raises_when_model_returns_none():
    client = ScriptedClient([None])
    a = _agent(client, Registry())
    with pytest.raises(AgentError, match="模型没有返回消息"):
        a.run("你好")


def test_run_raises_on_unsupported_tool_type():
    bad = SimpleNamespace(
        id="c", type="other", function=SimpleNamespace(name="read_file", arguments="{}")
    )
    client = ScriptedClient([_assistant(content=None, tool_calls=[bad])])
    a = _agent(client, Registry())
    with pytest.raises(AgentError, match="工具类型"):
        a.run("你好")


def test_run_raises_when_max_steps_exceeded():
    reg = _registry(_FakeTool("read_file", result="内容"))
    always_tool = _assistant(content=None, tool_calls=[_tool_call()])
    client = ScriptedClient([always_tool] * agent.MAX_STEPS)
    a = _agent(client, reg)
    with pytest.raises(AgentError, match="超过"):
        a.run("你好")


def test_run_stops_on_permission_failure():
    reg = _registry(_FakeTool("bash", error=ToolExecutionError("permission", "越界")))
    client = ScriptedClient(
        [_assistant(content=None, tool_calls=[_tool_call(name="bash", arguments='{"command":"rm"}')])]
    )
    a = _agent(client, reg)
    result = a.run("删点东西")
    assert result.startswith("本次运行已暂停")
