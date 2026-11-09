import json
from types import SimpleNamespace

from powercode_py.context.session import Session
from powercode_py.graph.agent import LangGraphAgent
from powercode_py.plan import AgentState
from powercode_py.tools.registry import Registry
from powercode_py.tools.submit_plan import SubmitPlanTool


def _assistant(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(name, arguments, tc_id="call_1"):
    return SimpleNamespace(
        id=tc_id, type="function", function=SimpleNamespace(name=name, arguments=arguments)
    )


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


class _FakeTool:
    def __init__(self, name, result="ok"):
        self.name = name
        self.definition = {"type": "function", "function": {"name": name}}
        self._result = result

    def execute(self, arguments_json):
        return self._result


def test_langgraph_direct_answer():
    client = ScriptedClient([_assistant(content="直接回答")])
    registry = Registry()
    registry.register(_FakeTool("read_file", result="# 内容"))
    agent = LangGraphAgent(client, registry, Session(), AgentState())
    assert agent.run("你好") == "直接回答"


def test_langgraph_tool_then_answer():
    client = ScriptedClient(
        [
            _assistant(content=None, tool_calls=[_tool_call("read_file", '{"path":"README.md"}')]),
            _assistant(content="这是答案"),
        ]
    )
    registry = Registry()
    registry.register(_FakeTool("read_file", result="# 内容"))
    agent = LangGraphAgent(client, registry, Session(), AgentState())
    result = agent.run("读一下")
    assert result == "这是答案"
    # 第二轮 call_model 的消息里应包含 tool 结果
    msgs = client.calls[1][0]
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": "# 内容"}


def test_langgraph_submit_plan_interrupts():
    state = AgentState("plan")
    registry = Registry()
    registry.register(SubmitPlanTool(state))
    client = ScriptedClient(
        [
            _assistant(
                content=None,
                tool_calls=[
                    _tool_call(
                        "submit_plan",
                        json.dumps({"title": "重构登录", "content": "## 目标\n重构", "steps": ["找到入口"]}),
                    )
                ],
            )
        ]
    )
    agent = LangGraphAgent(client, registry, Session(), state)
    result = agent.run("帮我规划")
    # interrupt 后 run 返回计划文本
    assert result.startswith("# 重构登录")
    assert state.get_status() == "waiting_for_approval"
