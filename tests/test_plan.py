import pytest

from powercode_py.plan import AgentState, PlanDraft, PlanError, format_plan


def _plan():
    return PlanDraft(title="重构登录", content="## 目标\n重构", steps=["找到入口", "加兼容层"])


def test_initial_code_mode():
    s = AgentState()
    assert s.get_mode() == "code"
    assert s.get_status() == "idle"


def test_enter_plan_sets_planning():
    s = AgentState()
    s.enter_plan()
    assert s.get_mode() == "plan"
    assert s.get_status() == "planning"


def test_submit_plan_only_in_planning():
    s = AgentState("plan")
    s.submit_plan(_plan())
    assert s.get_status() == "waiting_for_approval"
    assert s.get_pending_plan().title == "重构登录"


def test_submit_plan_in_code_raises():
    s = AgentState()
    with pytest.raises(PlanError, match="规划阶段"):
        s.submit_plan(_plan())


def test_approve_plan_flow():
    s = AgentState("plan")
    s.submit_plan(_plan())
    plan = s.approve_plan()
    assert plan.title == "重构登录"
    assert s.get_mode() == "code"
    assert s.get_status() == "executing"
    assert s.get_approved_plan().title == "重构登录"
    assert s.get_pending_plan() is None


def test_refine_plan():
    s = AgentState("plan")
    s.submit_plan(_plan())
    s.refine_plan()
    assert s.get_status() == "planning"


def test_cancel_plan():
    s = AgentState("plan")
    s.submit_plan(_plan())
    s.cancel_plan()
    assert s.get_mode() == "code"
    assert s.get_status() == "idle"
    assert s.get_pending_plan() is None


def test_finish_execution_clears_approved():
    s = AgentState("plan")
    s.submit_plan(_plan())
    s.approve_plan()
    s.finish_execution()
    assert s.get_status() == "idle"
    assert s.get_approved_plan() is None


def test_format_plan():
    assert format_plan(_plan()) == "# 重构登录\n\n## 目标\n重构\n"
