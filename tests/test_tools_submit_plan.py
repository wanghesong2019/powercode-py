import json

import pytest

from powercode_py.plan import AgentState
from powercode_py.tools.submit_plan import SubmitPlanTool
from powercode_py.tools.types import ToolError


def _args():
    return json.dumps(
        {
            "title": "重构登录",
            "content": "## 目标\n重构",
            "steps": ["找到入口", "加兼容层"],
        }
    )


def test_submit_plan_sets_waiting():
    state = AgentState("plan")
    tool = SubmitPlanTool(state)
    result = tool.execute(_args())
    assert result == "计划已提交，等待用户审批。"
    assert state.get_status() == "waiting_for_approval"
    assert state.get_pending_plan().title == "重构登录"


def test_submit_plan_invalid_steps():
    state = AgentState("plan")
    tool = SubmitPlanTool(state)
    with pytest.raises(ToolError, match="steps"):
        tool.execute(json.dumps({"title": "t", "content": "c", "steps": []}))
