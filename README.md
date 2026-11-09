# powercode-py

从零手搓 AI Agent（Python 版）—— 一份让读者照着文档无脑跟做的教学项目。

> 灵感与参考：[不用框架，手搓 AI Agent](https://juejin.cn/column/7661531339729829926)（作者：不一样的少年_ / GitHub: [Teernage/powercode](https://github.com/Teernage/powercode)）。本项目用纯 Python 重写并在原基础上补齐了 Plan Mode、错误自救与熔断、LangGraph 封装等模块。

## ✨ 功能

- 在终端中与 AI 模型对话（交互式多轮对话）
- 读取、创建/覆盖、编辑文件，列出目录、搜索文件
- 执行 shell 命令（构建、测试、运行代码）
- 多轮工具调用，最多 30 轮自动执行
- 工具注册机制，支持灵活扩展工具
- 会话上下文压缩，优化 token 使用
- Plan Mode：先出计划、人工审批、再执行，计划落盘为 `PLAN.md` / `TODO.md`
- 错误自救与熔断：失败自动重试、提示模型修复、连续失败自动暂停
- 可选 LangGraph 引擎：用 StateGraph 重写同一套 Agent Loop（`--engine langgraph`）

## 🛠️ 技术栈

- Python 3.10+
- OpenAI 兼容 SDK（可对接 DeepSeek、OpenAI 等）
- LangGraph（可选，通过 `--engine langgraph` 启用）

## 📦 安装

需要 Python 3.10+。

```bash
# 推荐：用 uv
uv venv
uv pip install -e .

# 或直接用 pip
pip install -e .
```

安装后即可在任意目录使用 `powercode` 命令。

## ⚙️ 配置

在项目根目录创建 `provider.json`（可先 `cp provider.json.example provider.json`）：

```json
{
  "baseURL": "https://api.deepseek.com",
  "apiKey": "你的 API Key",
  "model": "deepseek-v4-flash",
  "contextWindow": 128000
}
```

> 字段名沿用原作者的 camelCase 风格（`baseURL` / `apiKey` / `model` / `contextWindow`）。

配置文件查找顺序为「当前目录 → 用户目录 `~/.powercode/`」，也可以用 `--provider 路径` 显式指定。把配置放到 `~/.powercode/provider.json` 后，在任何目录都能直接运行。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置 API

复制并填写 `provider.json`（见上方「配置」）。

### 3. 运行

```bash
powercode "用一句话解释什么是 Python"
```

不带参数则进入交互模式：

```bash
powercode
> 帮我看看这个项目结构
> exit
```

交互模式下可用命令：`/plan` 进入 Plan Mode、`/code` 回到 Code Mode、`/status` 查看当前状态、`exit` / `quit` 退出。

### 4. 启用 LangGraph 引擎（可选）

```bash
pip install -e '.[graph]'
powercode --engine langgraph "读一下 README.md，一句话说这个项目是什么"
```

## 🔧 内置工具

| 工具 | 说明 |
|------|------|
| `read_file` | 读取项目内文本文件，超过 8KB 自动截断 |
| `write_file` | 创建或覆盖文件，目录不存在时自动创建 |
| `edit_file` | 精确替换文件中的一段唯一文本（需先读取） |
| `bash` | 在项目目录执行命令，30 秒超时，8KB 输出上限 |
| `list_files` | 递归列出项目内的文件和目录 |
| `search_files` | 在项目文本文件中搜索关键词 |
| `submit_plan` | 提交执行计划（仅 Plan Mode 可用） |

## 🧭 命令行参数

| 参数 | 说明 |
|------|------|
| `prompt` | 要发给模型的问题；不传则进入交互模式 |
| `--provider 路径` | 显式指定 provider.json 路径 |
| `--plan` | 启动后直接进入 Plan Mode |
| `--dir 目录` | Agent 操作的工作目录（默认当前目录） |
| `--engine {handmade,langgraph}` | 选择引擎（默认 handmade 手搓版） |

## 📖 学习路径

项目通过 git 提交历史组织成 8 个阶段，每个阶段都是可独立运行的代码。用 `git log --oneline` 即可一步步跟做。

1. **阶段一 · 对话**：封装 OpenAI 兼容客户端，实现一问一答（`config` / `chat` / `cli`）
2. **阶段二 · read_file**：接入第一个工具，让模型能读文件
3. **阶段三 · Agent Loop**：模型决定下一步 → 程序执行工具 → 结果回传的循环
4. **阶段四 · 工具注册中心**：统一的工具注册 / 分发 / 执行机制，一次性补全读写改跑
5. **阶段五 · 记忆压缩**：Session 会话历史 + 上下文压缩 + 交互循环
6. **阶段六 · Plan Mode**：计划审批状态机 + 只读工具边界 + 计划落盘
7. **阶段七 · 错误自救与熔断**：失败分类、恢复提示、RecoveryManager 熔断
8. **阶段八 · LangGraph 封装**：用 StateGraph 重写同一套 Agent Loop

配套的掘金专栏文章见 [手搓 AI Agent · Python 版](https://juejin.cn/column/7705955493571084328)。

## 📚 示例

`examples/` 目录提供一个不接真实模型的离线演示：

```bash
python examples/demo_recovery.py
```

它演示了「错误自救与熔断」的完整流程：`edit_file` 失败 → 返回恢复提示 → 模型读取修正 → 同一错误连续 3 次触发熔断暂停。

## 📁 项目结构

```
powercode_py/
├── cli.py             # 命令行入口：注册工具、解析参数、交互循环
├── agent.py           # Agent 主循环（手搓版）
├── chat.py            # 封装 OpenAI 兼容客户端
├── config.py          # 加载 provider.json 配置
├── plan.py            # Plan Mode 状态机
├── plan_files.py      # 计划批准后落盘为 PLAN.md / TODO.md
├── graph/
│   └── agent.py       # LangGraph 版 Agent（StateGraph）
├── context/
│   ├── session.py     # 会话历史
│   ├── compactor.py   # 上下文压缩 / 工作记忆
│   └── recovery.py    # 失败分类 + 恢复提示 + 熔断
└── tools/
    ├── types.py       # Tool 协议定义
    ├── registry.py    # 工具注册表（注册/分发/执行）
    ├── path.py        # 路径安全校验
    ├── read_file.py   # 读取文件
    ├── write_file.py  # 创建/覆盖文件
    ├── edit_file.py   # 编辑文件（精确替换）
    ├── bash.py        # 执行 shell 命令
    ├── list_files.py  # 列出目录
    ├── search_files.py# 搜索文本
    ├── submit_plan.py # 提交计划
    └── tool_runner.py # 工具批次执行器
```

## 🧪 测试

```bash
pip install -e '.[dev]'
python -m pytest
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
