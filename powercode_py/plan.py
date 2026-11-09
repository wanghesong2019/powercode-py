"""Plan Mode 状态机：mode / status / 待审批计划 / 已批准计划。"""

from dataclasses import dataclass


@dataclass
class PlanDraft:
    """待审批或已批准的计划：标题、Markdown 正文、执行步骤。"""

    title: str
    content: str
    steps: list[str]


class PlanError(Exception):
    """Plan 状态转换非法。"""


class AgentState:
    """保存 Plan Mode 运行状态，状态只能通过这些方法改变。"""

    def __init__(self, mode: str = "code"):
        self._mode = mode
        self._status = "planning" if mode == "plan" else "idle"
        self._pending_plan = None
        self._approved_plan = None

    def get_mode(self) -> str:
        return self._mode

    def get_status(self) -> str:
        return self._status

    def get_pending_plan(self):
        return self._pending_plan

    def get_approved_plan(self):
        return self._approved_plan

    def enter_plan(self) -> None:
        self._mode = "plan"
        self._status = "planning"
        self._pending_plan = None
        self._approved_plan = None

    def enter_code(self) -> None:
        self._mode = "code"
        self._status = "idle"
        self._pending_plan = None
        self._approved_plan = None

    def submit_plan(self, plan: PlanDraft) -> None:
        if self._mode != "plan" or self._status != "planning":
            raise PlanError("只有规划阶段可以提交计划。")
        self._pending_plan = plan
        self._status = "waiting_for_approval"

    def refine_plan(self) -> None:
        if self._status != "waiting_for_approval" or self._pending_plan is None:
            raise PlanError("当前没有等待修改的计划。")
        self._status = "planning"

    def approve_plan(self) -> PlanDraft:
        if self._status != "waiting_for_approval" or self._pending_plan is None:
            raise PlanError("当前没有等待批准的计划。")
        plan = self._pending_plan
        self._mode = "code"
        self._status = "executing"
        self._pending_plan = None
        self._approved_plan = plan
        return plan

    def cancel_plan(self) -> None:
        self._mode = "code"
        self._status = "idle"
        self._pending_plan = None
        self._approved_plan = None

    def finish_execution(self) -> None:
        if self._status == "executing":
            self._status = "idle"
            self._approved_plan = None


def format_plan(plan: PlanDraft) -> str:
    """把标题和正文拼成完整计划。"""
    return f"# {plan.title}\n\n{plan.content.strip()}\n"
