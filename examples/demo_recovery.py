"""离线演示：错误自救与熔断（不接真实模型）。"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from powercode_py.context.recovery import RecoveryManager
from powercode_py.tools.edit_file import EditFileTool
from powercode_py.tools.read_file import ReadFileTool
from powercode_py.tools.registry import Registry
from powercode_py.tools.tool_runner import run_tool_batch
from powercode_py.tools.types import ToolError


def _call(tc_id, name, args):
    return SimpleNamespace(
        id=tc_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def main():
    with tempfile.TemporaryDirectory() as d:
        work_dir = Path(d)
        (work_dir / "demo.txt").write_text("status=pending\n", encoding="utf-8")
        registry = Registry()
        registry.register(EditFileTool(work_dir))
        registry.register(ReadFileTool(work_dir))
        allowed = {"edit_file", "read_file"}

        recovery = RecoveryManager()
        first = run_tool_batch(
            [
                _call(
                    "1",
                    "edit_file",
                    {"path": "demo.txt", "old_text": "status=todo", "new_text": "status=done"},
                )
            ],
            registry,
            allowed,
            recovery,
        )
        print("\n".join(first["messages"][0]["content"].split("\n")[:4]))
        print()

        read = run_tool_batch(
            [_call("2", "read_file", {"path": "demo.txt"})], registry, allowed, recovery
        )
        print(f"读取结果：{read['messages'][0]['content'].strip()}")

        edit = run_tool_batch(
            [
                _call(
                    "3",
                    "edit_file",
                    {"path": "demo.txt", "old_text": "status=pending", "new_text": "status=done"},
                )
            ],
            registry,
            allowed,
            recovery,
        )
        print(edit["messages"][0]["content"])
        print(f"文件核验：{(work_dir / 'demo.txt').read_text().strip()}\n")

        # 同一错误调用累计失败 3 次触发暂停
        recovery2 = RecoveryManager()
        err = ToolError("没有找到 old_text，请先重新读取文件。")
        recovery2.on_failure("edit_file", "{}", err)
        recovery2.on_success("read_file", "{}")
        recovery2.on_failure("edit_file", "{}", err)
        third = recovery2.on_failure("edit_file", "{}", err)
        print("\n".join(third.output.split("\n")[-2:]))
        print(f"stop={third.stop}")


if __name__ == "__main__":
    main()
