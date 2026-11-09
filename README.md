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

1. 复制配置模板，填入你自己的 API Key：

```bash
cp provider.json.example provider.json
# 编辑 provider.json，填入 baseURL / apiKey / model
```

2. 运行：

```bash
powercode "用一句话解释什么是 Python"
```

它会打印出模型的中文回答。
