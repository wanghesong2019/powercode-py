"""powercode 命令行入口：注册工具并运行 Agent（支持 Plan Mode 与交互循环）。"""

import argparse
import sys
from pathlib import Path

from .agent import Agent, AgentError
from .chat import ChatClient, ChatError
from .config import ConfigError, load_config
from .context.session import Session
from .plan import AgentState
from .plan_files import save_approved_plan
from .tools.bash import BashTool
from .tools.edit_file import EditFileTool
from .tools.list_files import ListFilesTool
from .tools.read_file import ReadFileTool
from .tools.registry import Registry
from .tools.search_files import SearchFilesTool
from .tools.submit_plan import SubmitPlanTool
from .tools.write_file import WriteFileTool


def _build_agent(client, work_dir, state, engine="handmade"):
    """注册全部工具并创建一个带会话与状态的 Agent。"""
    registry = Registry()
    registry.register(ReadFileTool(work_dir))
    registry.register(ListFilesTool(work_dir))
    registry.register(SearchFilesTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(SubmitPlanTool(state))
    session = Session()
    if engine == "langgraph":
        try:
            from .graph.agent import LangGraphAgent
        except ImportError as exc:
            raise ConfigError("要使用 --engine langgraph 请先安装：pip install -e '.[graph]'") from exc
        return LangGraphAgent(client, registry, session, state)
    return Agent(client, registry, session, state)


def _print_status(state):
    print(f"当前模式：{state.get_mode()}")
    print(f"当前状态：{state.get_status()}")
    tools = (
        "read_file, list_files, search_files, submit_plan"
        if state.get_mode() == "plan"
        else "read_file, list_files, search_files, write_file, edit_file, bash"
    )
    print(f"可用工具：{tools}")


def _run_prompt(agent, value):
    print("AI 正在思考...\n")
    answer = agent.run(value)
    print(f"AI：{answer}")


def _review_pending_plan(agent, state, work_dir):
    while state.get_status() == "waiting_for_approval":
        print("\n请选择：\n1. 批准并执行\n2. 继续修改计划\n3. 取消\n")
        choice = input("选择：").strip()
        if choice == "1":
            plan = state.approve_plan()
            files = save_approved_plan(work_dir, plan)
            print("\n计划已批准，已进入 Code Mode。")
            print(f"已创建任务目录：{files['task_dir']}\n")
            _run_prompt(
                agent,
                f"计划已经批准。\n计划文件：{files['plan_path']}\n执行清单：{files['todo_path']}\n"
                "请先读取这两份文件，从第一项未完成任务开始执行；每完成一项后立即更新这份 TODO.md。",
            )
            return
        if choice == "2":
            feedback = input("请输入计划修改意见：").strip()
            if not feedback:
                print("修改意见不能为空。")
                continue
            state.refine_plan()
            _run_prompt(agent, f"请根据下面的反馈修改计划，并再次调用 submit_plan：\n{feedback}")
            continue
        if choice == "3":
            state.cancel_plan()
            print("\n计划已取消，已返回 Code Mode。")
            return
        print("请输入 1、2 或 3。")


def _interactive_loop(agent, state, work_dir):
    print("已进入交互模式，输入 exit 或 quit 退出。\n")
    while True:
        try:
            value = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not value:
            continue
        if value in ("exit", "quit"):
            break
        if value == "/plan":
            state.enter_plan()
            print("已进入 Plan Mode，只能读取和搜索项目。")
            continue
        if value == "/code":
            state.enter_code()
            print("已进入 Code Mode。")
            continue
        if value == "/status":
            _print_status(state)
            continue
        try:
            _run_prompt(agent, value)
            _review_pending_plan(agent, state, work_dir)
        except (ChatError, AgentError) as exc:
            print(f"本轮执行失败：{exc}")


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：`powercode "你的问题"` 单次执行，不带参数则进入交互模式。"""
    parser = argparse.ArgumentParser(
        prog="powercode",
        description="从零手搓的 AI Agent：支持 Plan Mode、读写改文件与执行命令。",
    )
    parser.add_argument("prompt", nargs="?", help="要发给模型的问题；不传则进入交互模式")
    parser.add_argument(
        "--provider",
        help="指定 provider.json 路径（默认按当前目录 → ~/.powercode/ 查找）",
    )
    parser.add_argument("--plan", action="store_true", help="启动后直接进入 Plan Mode")
    parser.add_argument("--dir", default=".", help="Agent 操作的工作目录（默认当前目录）")
    parser.add_argument(
        "--engine",
        choices=["handmade", "langgraph"],
        default="handmade",
        help="Agent 引擎（默认 handmade 手搓版）",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.provider)
        client = ChatClient(config)
        work_dir = Path(args.dir).resolve()
        state = AgentState("plan" if args.plan else "code")
        agent = _build_agent(client, work_dir, state, args.engine)
    except (ConfigError, ChatError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if args.prompt:
        try:
            _run_prompt(agent, args.prompt)
        except (ChatError, AgentError) as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        return 0

    _interactive_loop(agent, state, work_dir)
    return 0
