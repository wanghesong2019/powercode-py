"""提交实施计划并暂停等待审批的工具。"""

import json

from ..plan import AgentState, PlanDraft
from .types import ToolError


def _parse_string(args: dict, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{name} 必须是非空字符串。")
    return value.strip()


def _parse_string_array(args: dict, name: str) -> list[str]:
    value = args.get(name)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ToolError(f"{name} 必须是字符串数组。")
    if not value:
        raise ToolError(f"{name} 不能为空。")
    return [item.strip() for item in value]


def _parse_plan(arguments_json: str) -> PlanDraft:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"submit_plan 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict):
        raise ToolError("计划参数必须是对象。")
    return PlanDraft(
        title=_parse_string(args, "title"),
        content=_parse_string(args, "content"),
        steps=_parse_string_array(args, "steps"),
    )


class SubmitPlanTool:
    name = "submit_plan"

    definition = {
        "type": "function",
        "function": {
            "name": "submit_plan",
            "description": "提交最终实施计划，并暂停等待用户审批。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "计划标题"},
                    "content": {
                        "type": "string",
                        "description": "完整的 Markdown 计划正文，包含目标、方案、风险和验证方式，不重复一级标题",
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "按执行顺序排列的实施步骤",
                    },
                },
                "required": ["title", "content", "steps"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, state: AgentState):
        self.state = state

    def execute(self, arguments_json: str) -> str:
        plan = _parse_plan(arguments_json)
        self.state.submit_plan(plan)
        return "计划已提交，等待用户审批。"
