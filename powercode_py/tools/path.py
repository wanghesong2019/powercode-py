"""把路径限制在当前项目内的公共工具。"""

from pathlib import Path

from .types import ToolError


def resolve_in_work_dir(work_dir: str, relative_path: str) -> Path:
    """把相对路径解析成绝对路径，并确保它仍在工作目录内。"""
    if not relative_path.strip():
        raise ToolError("文件路径不能为空。")

    root = Path(work_dir).resolve()
    target = (root / relative_path).resolve()

    if target != root and root not in target.parents:
        raise ToolError("只能操作当前项目里的文件。")

    return target
