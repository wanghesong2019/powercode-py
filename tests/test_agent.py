from types import SimpleNamespace

import pytest

from powercode_py import agent
from powercode_py.agent import Agent, AgentError
from powercode_py.read_file import ReadFileError


def _assistant(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(name="read_file", arguments='{"path":"README.md"}', tc_id="call_1"):
    return SimpleNamespace(
        id=tc_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class ScriptedClient:
    """按顺序返回预设消息，并记录每次传入的 messages。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        if not self._responses:
            raise AssertionError("脚本化的响应用完了")
        return self._responses.pop(0)


def test_run_returns_answer_when_no_tool_call():
    client = ScriptedClient([_assistant(content="直接回答")])
    a = Agent(client)
    assert a.run("你好") == "直接回答"


def test_run_tool_then_answer(monkeypatch):
    monkeypatch.setattr(agent, "read_file_tool", lambda args: "# powercode")
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call()]),
            _assistant(content="这是一个教学项目"),
        ]
    )
    a = Agent(client)

    result = a.run("这个项目是做什么的？")

    assert result == "这是一个教学项目"
    msgs = client.calls[1]
    assert msgs[0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
    assert msgs[1] == {"role": "user", "content": "这个项目是做什么的？"}
    assert msgs[2]["role"] == "assistant"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "read_file"
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": "# powercode"}


def test_run_handles_multiple_tool_calls_in_one_round(monkeypatch):
    monkeypatch.setattr(agent, "read_file_tool", lambda args: "内容")
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
    a = Agent(client)

    result = a.run("读两个文件")

    assert result == "读完了"
    msgs = client.calls[1]
    assert msgs[3] == {"role": "tool", "tool_call_id": "c1", "content": "内容"}
    assert msgs[4] == {"role": "tool", "tool_call_id": "c2", "content": "内容"}


def test_run_feeds_back_tool_failure(monkeypatch):
    def boom(args):
        raise ReadFileError("文件不存在")

    monkeypatch.setattr(agent, "read_file_tool", boom)
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call()]),
            _assistant(content="文件找不到"),
        ]
    )
    a = Agent(client)

    result = a.run("读个不存在的文件")

    assert result == "文件找不到"
    msgs = client.calls[1]
    assert msgs[3]["role"] == "tool"
    assert msgs[3]["content"].startswith("读取失败")


def test_run_raises_when_model_returns_none():
    client = ScriptedClient([None])
    a = Agent(client)
    with pytest.raises(AgentError, match="模型没有返回消息"):
        a.run("你好")


def test_run_raises_on_unsupported_tool_type():
    bad = SimpleNamespace(
        id="c",
        type="other",
        function=SimpleNamespace(name="read_file", arguments="{}"),
    )
    client = ScriptedClient([_assistant(content=None, tool_calls=[bad])])
    a = Agent(client)
    with pytest.raises(AgentError, match="工具类型"):
        a.run("你好")


def test_run_raises_on_unsupported_tool_name():
    client = ScriptedClient(
        [_assistant(content=None, tool_calls=[_tool_call(name="write_file")])]
    )
    a = Agent(client)
    with pytest.raises(AgentError, match="工具"):
        a.run("你好")


def test_run_raises_when_max_steps_exceeded(monkeypatch):
    monkeypatch.setattr(agent, "read_file_tool", lambda args: "内容")
    always_tool = _assistant(content=None, tool_calls=[_tool_call()])
    client = ScriptedClient([always_tool] * agent.MAX_STEPS)
    a = Agent(client)
    with pytest.raises(AgentError, match="超过"):
        a.run("你好")
