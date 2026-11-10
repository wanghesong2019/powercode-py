"""LangGraph 版 Agent：把 Agent Loop 重写成 StateGraph。"""

from types import SimpleNamespace
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from ..agent import (
    CODE_TOOL_NAMES,
    CORE_SYSTEM_PROMPT,
    EXECUTION_PROMPT,
    PLAN_MODE_PROMPT,
    PLAN_TOOL_NAMES,
    AgentError,
)
from ..context.compactor import Compactor
from ..context.recovery import RecoveryManager
from ..context.session import Session
from ..plan import AgentState, format_plan
from ..tools.registry import Registry
from ..tools.tool_runner import run_tool_batch


class GraphState(TypedDict, total=False):
    tool_calls: list
    answer: str


class LangGraphAgent:
    """用 LangGraph StateGraph 重写的 Agent，复用 Registry / Session / Recovery / Compactor。"""

    def __init__(self, client, registry: Registry, session: Session, state: AgentState):
        self.client = client
        self.registry = registry
        self.session = session
        self.state = state
        self.compactor = Compactor(client, client.get_context_window())
        self.recovery = RecoveryManager()
        self._graph = self._build_graph()

    def _tool_calls_dicts(self, message) -> list:
        """把模型返回的 tool_calls 转成可序列化的 dict 列表。"""
        tool_calls = getattr(message, "tool_calls", None) or []
        return [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ]

    def _assistant_message(self, message) -> dict:
        msg = {"role": "assistant", "content": message.content}
        # DeepSeek thinking mode：reasoning_content 必须在多轮里原样传回，否则 400
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning:
            msg["reasoning_content"] = reasoning
        tool_calls = self._tool_calls_dicts(message)
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg

    def _allowed_tool_names(self):
        return PLAN_TOOL_NAMES if self.state.get_mode() == "plan" else CODE_TOOL_NAMES

    def _build_system_prompt(self) -> str:
        if self.state.get_mode() == "plan":
            return CORE_SYSTEM_PROMPT + PLAN_MODE_PROMPT
        approved = self.state.get_approved_plan()
        if approved:
            return CORE_SYSTEM_PROMPT + EXECUTION_PROMPT + f"\n\n{format_plan(approved)}"
        return CORE_SYSTEM_PROMPT

    def _call_model(self, state: GraphState) -> dict:
        memory = self.compactor.build_working_memory(self.session)
        allowed = self._allowed_tool_names()
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            *memory,
        ]
        completion = self.client.complete_with_usage(
            messages, self.registry.get_definitions(allowed)
        )
        message = completion.message
        if message is None:
            raise AgentError("模型没有返回消息。")

        raw_calls = getattr(message, "tool_calls", None) or []
        for call in raw_calls:
            if call.type != "function":
                raise AgentError(f"暂时不支持工具类型：{call.type}")

        self.session.append(self._assistant_message(message))
        if completion.total_tokens is not None and completion.total_tokens > 0:
            self.session.save_usage(completion.total_tokens)

        if not raw_calls:
            self.state.finish_execution()
            return {"answer": message.content or "模型没有返回文本内容。", "tool_calls": []}
        return {"tool_calls": self._tool_calls_dicts(message)}

    def _run_tools(self, state: GraphState) -> dict:
        allowed = self._allowed_tool_names()
        calls = [
            SimpleNamespace(
                id=c["id"],
                type=c["type"],
                function=SimpleNamespace(
                    name=c["function"]["name"], arguments=c["function"]["arguments"]
                ),
            )
            for c in state.get("tool_calls", [])
        ]
        batch = run_tool_batch(calls, self.registry, allowed, self.recovery)
        self.session.append(*batch["messages"])

        if batch["stop"]:
            return {
                "answer": (
                    f"本次运行已暂停。\n{batch['stop_reason']}\n"
                    "请检查当前文件和未完成 TODO 后再继续。"
                ),
                "tool_calls": [],
            }

        if self.state.get_status() == "waiting_for_approval":
            plan = self.state.get_pending_plan()
            if plan is None:
                raise AgentError("计划状态异常。")
            # 暂停图，把计划交给 CLI 审批；批准后由 CLI 发起新一轮执行。
            interrupt({"title": plan.title, "plan": format_plan(plan)})

        return {"tool_calls": []}

    def _should_continue(self, state: GraphState) -> str:
        return "run_tools" if state.get("tool_calls") else END

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("call_model", self._call_model)
        graph.add_node("run_tools", self._run_tools)
        graph.set_entry_point("call_model")
        graph.add_conditional_edges(
            "call_model", self._should_continue, {"run_tools": "run_tools", END: END}
        )
        graph.add_edge("run_tools", "call_model")
        return graph.compile(checkpointer=MemorySaver())

    def run(self, prompt: str) -> str:
        """运行图，返回最终回答；若被 plan interrupt 打断，返回计划文本。"""
        if self.state.get_status() == "waiting_for_approval":
            raise AgentError("当前计划正在等待审批。")

        self.session.append({"role": "user", "content": prompt})
        self.recovery = RecoveryManager()

        result = self._graph.invoke(
            {"tool_calls": [], "answer": ""},
            {"configurable": {"thread_id": str(uuid4())}},
        )

        if "__interrupt__" in result:
            plan = self.state.get_pending_plan()
            return format_plan(plan) if plan else ""
        return result.get("answer", "")
