"""工具注册中心：统一注册、查询、执行工具。"""

from .types import Tool, ToolError


class Registry:
    """按名字保存工具，供 Agent 统一分发。"""

    def __init__(self):
        self._tools = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具；重名则报错。"""
        if tool.name in self._tools:
            raise ToolError(f"工具重复注册：{tool.name}")
        self._tools[tool.name] = tool

    def get_definitions(self, allowed_names=None) -> list[dict]:
        """返回工具说明；传 allowed_names 时只返回允许的工具。"""
        return [
            tool.definition
            for tool in self._tools.values()
            if allowed_names is None or tool.name in allowed_names
        ]

    def execute(self, name: str, arguments_json: str, allowed_names=None) -> str:
        """根据工具名找到工具并执行；传 allowed_names 时先做权限拦截。"""
        if allowed_names is not None and name not in allowed_names:
            raise ToolError(f"当前模式不允许调用工具：{name}")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"找不到工具：{name}")
        return tool.execute(arguments_json)
