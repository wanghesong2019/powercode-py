# powercode-py

从零手搓 AI Agent（Python 版）—— 一份让读者照着文档无脑跟做的教学项目。

> 灵感与参考：[不用框架，手搓 AI Agent](https://juejin.cn/column/7661531339729829926)（作者：不一样的少年_ / GitHub: [Teernage/powercode](https://github.com/Teernage/powercode)）

## 这是什么

一个不依赖任何 Agent 框架、用纯 Python 从零实现的终端 coding agent。跟着文档一步步开发、提交，每一步都能得到一个可运行的功能。

## 安装

需要 Python 3.10+。

```bash
uv venv
uv pip install -e .
```

不用 uv 的话，也可以直接用 pip：

```bash
pip install -e .
```

## 快速开始

1. 准备配置（二选一）：

**方式一：放在当前目录**（在项目根目录执行）

```bash
cp provider.json.example provider.json
```

**方式二：放在用户目录**，这样在任何目录都能运行

```bash
# Linux / macOS
mkdir -p ~/.powercode && cp provider.json.example ~/.powercode/provider.json
# Windows PowerShell
mkdir $HOME\.powercode; copy provider.json.example $HOME\.powercode\provider.json
```

然后编辑配置文件，填入你自己的 `baseURL` / `apiKey` / `model`。

2. 运行：

```bash
powercode "用一句话解释什么是 Python"
```

它会打印出模型的中文回答。

> `provider.json` 的查找顺序是「当前目录 → `~/.powercode/`」；也可以用 `--provider 路径` 显式指定。
