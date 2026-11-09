from types import SimpleNamespace

import pytest

from powercode_py import agent
from powercode_py.agent import Agent, AgentError
from powercode_py.tools.registry import Registry
from powercode_py.tools.types import ToolError


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


class ScriptedClient:
    """按顺序返回预设消息，记录每次传入的 (messages, tools)。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if not self._responses:
            raise AssertionError("脚本化的响应用完了")
        return self._responses.pop(0)


def _registry(tool):
    r = Registry()
    r.register(tool)
    return r


def test_run_returns_answer_when_no_tool_call():
    client = ScriptedClient([_assistant(content="直接回答")])
    a = Agent(client, Registry())
    assert a.run("你好") == "直接回答"


def test_run_tool_then_answer():
    reg = _registry(_FakeTool("read_file", result="# 内容"))
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call()]),
            _assistant(content="这是答案"),
        ]
    )
    a = Agent(client, reg)

    result = a.run("这个项目是做什么的？")

    assert result == "这是答案"
    msgs = client.calls[1][0]
    assert msgs[0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
    assert msgs[1] == {"role": "user", "content": "这个项目是做什么的？"}
    assert msgs[2]["role"] == "assistant"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": "# 内容"}
    assert client.calls[0][1] == reg.get_definitions()


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
    a = Agent(client, reg)
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
    a = Agent(client, reg)
    result = a.run("读个不存在的文件")
    assert result == "文件找不到"
    msgs = client.calls[1][0]
    assert msgs[3]["role"] == "tool"
    assert msgs[3]["content"].startswith("工具执行失败")


def test_run_feeds_back_unknown_tool():
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call(name="nope")]),
            _assistant(content="没这个工具"),
        ]
    )
    a = Agent(client, Registry())
    result = a.run("hi")
    assert result == "没这个工具"
    msgs = client.calls[1][0]
    assert "找不到工具" in msgs[3]["content"]


def test_run_raises_when_model_returns_none():
    client = ScriptedClient([None])
    a = Agent(client, Registry())
    with pytest.raises(AgentError, match="模型没有返回消息"):
        a.run("你好")


def test_run_raises_on_unsupported_tool_type():
    bad = SimpleNamespace(
        id="c",
        type="other",
        function=SimpleNamespace(name="read_file", arguments="{}"),
    )
    client = ScriptedClient([_assistant(content=None, tool_calls=[bad])])
    a = Agent(client, Registry())
    with pytest.raises(AgentError, match="工具类型"):
        a.run("你好")


def test_run_raises_when_max_steps_exceeded():
    reg = _registry(_FakeTool("read_file", result="内容"))
    always_tool = _assistant(content=None, tool_calls=[_tool_call()])
    client = ScriptedClient([always_tool] * agent.MAX_STEPS)
    a = Agent(client, reg)
    with pytest.raises(AgentError, match="超过"):
        a.run("你好")
