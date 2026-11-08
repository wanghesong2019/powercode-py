# powercode-py 设计文档

> 记录日期：2026-11-08
> 状态：待批准（批准后进入实施计划阶段）
> 前置文档：[语言选型.md](./语言选型.md)

## 1. 意图与动机

把 Teernage 的「[不用框架，手搓 AI Agent](https://juejin.cn/column/7661531339729829926)」TypeScript 教学专栏，用 **Python 原创重实现**（移植，非 fork、非改原作者代码），服务于四个目标：

- **a) 吃透细节**：以 Python 视角逐阶段重写，边移植边掌握 coding agent 的技术原理（Agent Loop、工具注册、上下文压缩、Plan 审批、错误恢复）。
- **b) 读者可实操的开源项目**：核心交付物是一份**"读者无脑跟做"的详细开发文档**（对应掘金博客）+ 一条 commit 轨迹（对应仓库历史）。读者照着文档一步步开发、修改、提交，**每做完一步即得到对应的功能实现**；步骤间穿插原理讲解（类似参考文献的"为什么这样做"解读），并在详尽基础上**控制博客篇幅**；开源后争取社区认可（star）。
- **c) 去 demo 味**：调研主流 coding agent 后，补充生产化模块（测试、配置、日志、持久化、错误处理等）。
- **d) LangGraph 封装**：第 8 阶段用 LangGraph 重写封装，回到要长期深耕的框架。

## 2. 目标 / 非目标 / 反目标

### 目标

1. 忠实移植 7 篇，形成 7 个可运行的阶段（对应原专栏 7 篇文章）。
2. 一条"每个 commit = 一个读者可无脑跟做的开发步骤"的干净线性 commit 轨迹，与博客章节一一对应。
3. 最终形态：`pip install` 的 Python 包 `powercode-py`，terminal CLI（`powercode` 命令）。
4. 第 8 阶段用 LangGraph 重写封装（StateGraph + interrupt + checkpointer）。
5. 补充测试、文档、配置，让项目脱离"教学 demo 味"。
6. 为后续持续迭代预留模块扩展接口（工具注册、provider、存储、agent 生命周期钩子等）。

### 非目标

- 不改动原作者代码（不是 fork 原仓库）。
- 不做 VS Code 插件形态。
- 不逐行 1:1 复刻代码——用 Python 表达同样的原理与阶段演进。

### 反目标（满足以下任一即视为失败）

- 变成"只教 LangGraph 而丢掉从零手搓的教学价值"。
- 沦为无测试、无文档、只能跑一次 demo 的玩具。
- 未署名/致谢原作者，产生抄袭嫌疑。
- commit 历史混乱，读者无法跟随。

## 3. 约束与既定决策

| 项 | 决策 |
|----|------|
| 语言 | Python 3（具体版本以 33 服务器为准，目标 3.11+） |
| 性质 | 原创重实现/移植，非重构 |
| 项目名 | `powercode-py`（延续 powercode，README 致谢 Teernage 并附专栏链接） |
| 参考文献 | 仅「手搓 AI Agent」7 篇（已下载至 `./juejin-column/`） |
| 产品形态 | pip 包 + `[project.scripts]` 入口；CLI 薄壳 + LangGraph 核心库（第 8 阶段后） |
| 架构主线 | 手搓 7 阶段 + 第 8 阶段 LangGraph 收尾 |
| commit 轨迹 | 每个 commit = 一个读者可无脑跟做的步骤，线性演进，与博客章节一一对应 |
| LLM | OpenAI 兼容 SDK（DeepSeek/OpenAI 等），配置走 `provider.json` 或 `.env` |
| 开发环境 | 本地 Windows 写代码；**运行/测试在 33 服务器**（kaiChen@115.233.223.42:20036 → hermes） |
| 工具链 | 待定（uv 或 pip+venv，取决于 33 服务器现状） |
| 发布节奏 | 博客随项目进度**及时发布**（完成一篇即发，不堆积），据阅读/收藏/点赞反馈及时调整博客风格 |
| 博客风格 | 参照 powercode 原作者（Teernage）专栏行文风格；7 篇原文已下载至 `./juejin-column/` 作风格参照 |

**待确认**：33 服务器的 Python 版本、是否已有 uv/pip、网络可达性（能否访问 DeepSeek API）——进入实施阶段前用 `connect-33-server` 技能核实。

## 4. 阶段划分（对应 7 篇 + LangGraph 收尾）

| 阶段 | 对应文章 | 能力 |
|------|---------|------|
| 1 | (一) 先让它跑起来 | 一问一答，chat client，项目骨架 |
| 2 | 给大模型装上"手" | `read_file` 工具 |
| 3 | 手搓一个 Agent Loop | 多轮工具调用循环 |
| 4 | 答案藏在这 4 个工具里 | 工具注册表 + read/write/edit/bash + 路径安全边界 |
| 5 | 对话记忆与上下文压缩 | Session + Compactor（token 记账 + 摘要压缩） |
| 6 | 先别改代码 | Plan Mode + 审批状态机 + 任务清单存档 |
| 7 | 错误自救与熔断 | 错误分类 + 调用指纹记账 + 批次熔断恢复 |
| 8 | （LangGraph 收尾） | 用 StateGraph 重写：节点/条件边 + interrupt 审批 + checkpointer 恢复 |

**关键张力与化解**：目标 a/b 要求"从零手搓"（教学价值），目标 d 要求"LangGraph 封装"（工业价值）。方案——**前 7 阶段纯手搓，第 8 阶段用 LangGraph 重写同一套能力**，两者在同一仓库同一演进线上，读者既能看懂原理、又能看到原理如何映射到工业框架（agent loop → node/edge，审批 → interrupt，恢复 → checkpointer）。

**开发与发布节奏**：开发与写作**交替进行、随做随发，不堆积**。节奏为——完成一个阶段（含各跟做步骤的 commit）→ 写对应博客文章 → 发布掘金 → 收集阅读/收藏/点赞反馈 → 据反馈调整博客风格与后续写法 → 进入下一阶段。用真实反馈持续校准风格，而非憋到最后一次性放 7 篇。

## 5. commit 轨迹设计

原则：**每个 commit = 文档/博客里的一个"跟做步骤"**——细到读者能无脑照做（无需自己补设计）、粗到博客篇幅可控（每篇通常 3~5 个 commit）。commit 与博客章节一一对应：读者做完一节、提交一个 commit，即得到对应的功能实现。

以阶段 4（工具注册表）为例的拆分示例：

```
feat(agent): 引入 Tool 接口与 Registry
feat(tools): 实现 read_file 工具
feat(tools): 实现 write_file 工具
feat(tools): 实现 edit_file 工具
feat(tools): 实现 bash 工具
feat(agent): 接入主循环，支持多工具分发
```

每个阶段拆 3~6 个 commit，整体形成一条从简到繁、每步可 checkout 的演进线。commit message 采用 Conventional Commits 风格（`feat`/`refactor`/`test`/`docs`），便于读者和后续专栏写作直接引用。

## 6. 目标 c：调研与去 demo 味

进入阶段 7 之后、阶段 8 之前，调研主流 coding agent（Claude Code、Cursor、Cline、Aider、OpenHands、Codex、Goose 等），产出一份模块对照，确定可补充的生产化能力。候选方向（调研后取舍）：

- 流式输出（SSE/逐 token）
- 会话持久化与恢复（跨进程）
- 多 provider 支持
- MCP 工具协议
- 结构化日志
- 测试（pytest + mock LLM）
- 配置校验、错误边界

## 7. 模块扩展接口（架构原则）

为后续持续迭代（目标 c 的新模块）预留接口，避免加功能就要改主循环。核心扩展点：

- **工具注册表**：新工具只需实现 `Tool` 接口并注册，Agent 主循环零改动（阶段 4 即奠定）。
- **LLM Provider 抽象**：`ChatClient` 定义统一接口，DeepSeek / OpenAI / 其他 provider 通过配置切换，不硬编码。
- **存储/持久化抽象**：Session / checkpoint 后端可替换（内存 → 文件 → 数据库），为第 8 阶段 LangGraph checkpointer 与后续跨进程持久化铺路。
- **Agent 生命周期钩子**：在"调用前 / 工具执行后 / 失败时"等节点预留 hook，让错误恢复、日志、遥测以插件方式接入，而非散落主循环。
- **模式抽象（Plan / Code）**：模式作为可配置的策略，便于后续扩展更多模式（review、多步 agentic 等）。

原则：**每个阶段先搭好最小可用的接口，再填充实现**；宁可接口早抽象一步，不留"后面加功能要改主循环"的债。

## 8. 留给实施阶段的决策（builder 的自主空间）

- 库选型：CLI 用 `argparse`/`typer`/`click`，TUI 用 `rich`/`prompt_toolkit`，LLM 客户端用 `openai` SDK 或 `litellm`。
- Python 包布局（`src` 布局 vs 平铺）、`pyproject.toml` 细节。
- 测试框架（`pytest`）与 mock 策略。
- 各阶段 commit 的精确拆分粒度与边界。
- LangGraph 版本锁定与 checkpoint 后端选择。

## 9. 验收口径

- 读者照着文档步骤开发，每完成一步（一个 commit）都能跑通对应功能，最终 7 阶段全部可运行；`git checkout` 到任一 commit 都能复现。
- `pip install powercode-py` 后，`powercode` 命令可用（交互式 + 一次性 prompt + plan 模式）。
- 第 8 阶段 LangGraph 版与手搓版行为对齐（同一组任务产出等价结果）。
- 有 README、贡献指南、至少覆盖核心模块的测试。
