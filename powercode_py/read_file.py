"""read_file 工具：读取当前项目内的文本文件。"""

import json
from pathlib import Path

MAX_BYTES = 8_000  # 最大字节数


class ReadFileError(Exception):
    """read_file 工具执行失败。"""


READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取当前项目中的文本文件内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，比如 README.md",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
}


def _get_path(arguments_json: str) -> str:
    """从工具调用参数中解析并校验 path。"""
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ReadFileError(f"read_file 参数不是合法 JSON：{exc}") from exc

    if not isinstance(args, dict) or not isinstance(args.get("path"), str):
        raise ReadFileError("read_file 需要传入文件路径。")

    path = args["path"].strip()
    if not path:
        raise ReadFileError("read_file 需要传入文件路径。")

    return path


def read_file_tool(arguments_json: str) -> str:
    """读取当前项目内的文本文件，返回内容。"""
    relative_path = _get_path(arguments_json)

    work_dir = Path.cwd().resolve()
    target_path = (work_dir / relative_path).resolve()

    if work_dir != target_path and work_dir not in target_path.parents:
        raise ReadFileError("只能读取当前项目里的文件。")

    if not target_path.exists():
        raise ReadFileError(f"文件不存在：{relative_path}")

    if target_path.is_dir():
        raise ReadFileError(f"这是一个目录，不是文件：{relative_path}")

    data = target_path.read_bytes()

    if len(data) > MAX_BYTES:
        head = data[:MAX_BYTES].decode("utf-8", errors="replace")
        return f"{head}\n\n...[文件太长了，只返回前 {MAX_BYTES} 个字节]..."

    return data.decode("utf-8", errors="replace")
