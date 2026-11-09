from powercode_py.plan import PlanDraft
from powercode_py.plan_files import save_approved_plan


def test_save_approved_plan_creates_files(tmp_path):
    plan = PlanDraft(title="重构登录模块", content="## 目标\n重构", steps=["找到入口", "加兼容层"])
    files = save_approved_plan(tmp_path, plan)
    plan_file = tmp_path / files["plan_path"]
    todo_file = tmp_path / files["todo_path"]
    assert plan_file.exists()
    assert todo_file.exists()
    assert "# 重构登录模块" in plan_file.read_text(encoding="utf-8")
    todo_text = todo_file.read_text(encoding="utf-8")
    assert "- [ ] 找到入口" in todo_text
    assert "- [ ] 加兼容层" in todo_text


def test_task_name_sanitized(tmp_path):
    plan = PlanDraft(title="重构/登录..模块", content="c", steps=["s"])
    files = save_approved_plan(tmp_path, plan)
    assert ".." not in files["task_dir"]
    assert files["task_dir"].startswith(".powercode/tasks/")
