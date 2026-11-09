"""把批准的计划落盘为 PLAN.md 和 TODO.md。"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .plan import PlanDraft, format_plan


def _create_task_name(title: str) -> str:
    """把计划标题转成安全目录名，并带上毫秒时间戳。"""
    safe = unicodedata.normalize("NFKC", title).strip().lower()
    safe = re.sub(r"[^\w]", "-", safe)
    safe = safe.strip("-")[:60].rstrip("-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]
    return f"{timestamp}-{safe or 'plan'}"


def _format_todo(plan: PlanDraft) -> str:
    steps = "\n".join(f"- [ ] {step}" for step in plan.steps)
    return f"# 执行清单\n\n> 这份清单由已经批准的 PLAN.md 生成。\n\n## 实现步骤\n\n{steps}\n"


def save_approved_plan(work_dir, plan: PlanDraft) -> dict:
    """在 .powercode/tasks/<plan-name>/ 下写入 PLAN.md 和 TODO.md。"""
    task_name = _create_task_name(plan.title)
    task_dir = Path(".powercode") / "tasks" / task_name
    plan_path = task_dir / "PLAN.md"
    todo_path = task_dir / "TODO.md"

    absolute_task_dir = Path(work_dir) / task_dir
    absolute_task_dir.mkdir(parents=True, exist_ok=True)
    (Path(work_dir) / plan_path).write_text(format_plan(plan), encoding="utf-8")
    (Path(work_dir) / todo_path).write_text(_format_todo(plan), encoding="utf-8")

    return {
        "task_dir": task_dir.as_posix(),
        "plan_path": plan_path.as_posix(),
        "todo_path": todo_path.as_posix(),
    }
