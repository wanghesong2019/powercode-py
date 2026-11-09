"""工具统一接口。"""

from typing import Protocol


class ToolError(Exception):
    """工具执行或参数校验失败。"""


class Tool(Protocol):
    """一个工具要交齐的三样东西：name、definition、execute。"""

    name: str
    definition: dict

    def execute(self, arguments_json: str) -> str:
        """真正执行工具，返回结果文本。"""
        ...
