"""Agent：把模型、工具注册中心、会话记忆、状态机串起来的核心循环。"""

from .chat import ChatClient
from .context.compactor import Compactor
from .context.recovery import RecoveryManager
from .context.session import Session
from .plan import AgentState, format_plan
from .tools.registry import Registry
from .tools.tool_runner import run_tool_batch

MAX_STEPS = 30

CORE_SYSTEM_PROMPT = """你是 powercode-py，一个研发助手。
请优先读取真实文件；修改后主动运行命令验证结果；请使用中文回答。
所有文件路径都相对于当前工作目录，不能操作工作目录之外的文件。
工具失败后，结合原始日志和 Harness 恢复提示调整策略。
超时、输出溢出或写入报错后，先检查进程和文件现状，不能假定操作完全没有生效。
验证未通过时，不得把对应 TODO 标为完成；不能通过删除测试或绕过权限消除报错。
"""

PLAN_MODE_PROMPT = """
# 当前模式：Plan Mode

你现在只能研究项目和制定计划，不能修改文件或执行命令。

请按以下顺序工作：
1. 先使用 list_files、search_files 和 read_file 了解真实项目。
2. 能从项目中找到的答案，不要询问用户。
3. 只有关键需求或取舍无法从项目确认时，才向用户提出问题并等待回答。
4. 不要把普通猜测写成已经确定的事实。
5. content 必须是一份完整的 Markdown 计划正文，写清目标、方案、风险和验证方式，不重复 title 对应的一级标题。
6. steps 必须从 content 的实施方案中提炼，按执行顺序排列，并包含必要的验证步骤。
7. content 和 steps 不能出现两套不同的方案。
8. 计划完成后必须调用 submit_plan，不要只输出一段普通 Markdown。
"""

EXECUTION_PROMPT = """
# 当前模式：Code Mode

下面的计划已经由用户批准。

批准消息会给出本次任务的 PLAN.md 和 TODO.md 路径。
请先读取这两份文件，然后按照 TODO.md 从上到下执行。

- 完成一个有结果的步骤后，立即把对应的 - [ ] 更新为 - [x]。
- 修改代码但还没有完成对应验证时，不能勾选包含验证工作的步骤。
- 遇到错误时先读取本次任务的 TODO.md 确认当前位置，再修复并重新验证。
- 不得擅自改变已经批准的目标和范围。
"""

PLAN_TOOL_NAMES = {"read_file", "list_files", "search_files", "submit_plan"}
CODE_TOOL_NAMES = {
    "read_file",
    "list_files",
    "search_files",
    "write_file",
    "edit_file",
    "bash",
}


class AgentError(Exception):
    """Agent 运行失败。"""


class Agent:
    """一个最小 Agent：循环调用模型，直到它不再申请工具。"""

    def __init__(self, client: ChatClient, registry: Registry, session: Session, state: AgentState):
        self.client = client
        self.registry = registry
        self.session = session
        self.state = state
        self.compactor = Compactor(client, client.get_context_window())

    def _assistant_message(self, message) -> dict:
        """把模型返回的消息转成可回传的 assistant 消息 dict。"""
        msg = {"role": "assistant", "content": message.content}
        # DeepSeek thinking mode：reasoning_content 必须在多轮里原样传回，否则 400
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning:
            msg["reasoning_content"] = reasoning
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ]
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

    def run(self, prompt: str) -> str:
        """运行 Agent 循环，返回最终回答文本。"""
        if self.state.get_status() == "waiting_for_approval":
            raise AgentError("当前计划正在等待审批。")

        self.session.append({"role": "user", "content": prompt})

        # 每次 run 使用独立计数；上下文压缩不会清空本次计数。
        recovery = RecoveryManager()

        for step in range(1, MAX_STEPS + 1):
            memory = self.compactor.build_working_memory(self.session)
            allowed = self._allowed_tool_names()
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                *memory,
            ]

            completion = self.client.complete_with_usage(
                messages,
                self.registry.get_definitions(allowed),
            )
            message = completion.message

            if message is None:
                raise AgentError("模型没有返回消息。")

            tool_calls = getattr(message, "tool_calls", None) or []
            for call in tool_calls:
                if call.type != "function":
                    raise AgentError(f"暂时不支持工具类型：{call.type}")

            self.session.append(self._assistant_message(message))

            if completion.total_tokens is not None and completion.total_tokens > 0:
                self.session.save_usage(completion.total_tokens)

            if not tool_calls:
                self.state.finish_execution()
                return message.content or "模型没有返回文本内容。"

            batch = run_tool_batch(tool_calls, self.registry, allowed, recovery)
            self.session.append(*batch["messages"])

            if batch["stop"]:
                return (
                    f"本次运行已暂停。\n{batch['stop_reason']}\n"
                    "请检查当前文件和未完成 TODO 后再继续。"
                )

            if self.state.get_status() == "waiting_for_approval":
                plan = self.state.get_pending_plan()
                if plan is None:
                    raise AgentError("计划状态异常。")
                return format_plan(plan)

        raise AgentError(f"执行超过 {MAX_STEPS} 轮，已停止。")
