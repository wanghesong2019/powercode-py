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

    def get_definitions(self) -> list[dict]:
        """返回所有工具的 definition（给模型看的工具说明）。"""
        return [tool.definition for tool in self._tools.values()]

    def execute(self, name: str, arguments_json: str) -> str:
        """根据工具名找到工具并执行。"""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"找不到工具：{name}")
        return tool.execute(arguments_json)
