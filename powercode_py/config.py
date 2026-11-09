"""加载并校验 provider.json 配置。"""

import json
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """配置加载或校验失败。"""


@dataclass
class Config:
    """运行所需的 provider 配置（snake_case 字段）。"""

    base_url: str
    api_key: str
    model: str
    context_window: int


DEFAULT_FILENAME = "provider.json"


def _candidate_paths() -> list[Path]:
    """按优先级返回查找配置的候选路径：当前目录 → 用户目录 ~/.powercode/。"""
    return [
        Path.cwd() / DEFAULT_FILENAME,
        Path.home() / ".powercode" / DEFAULT_FILENAME,
    ]


def _load(path: Path) -> Config:
    """读取并校验指定路径的 provider.json。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件 {path} 不是合法的 JSON：{exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"配置文件 {path} 顶层必须是 JSON 对象。")

    field_map = {
        "baseURL": "base_url",
        "apiKey": "api_key",
        "model": "model",
    }
    invalid = [
        key
        for key in field_map
        if not isinstance(raw.get(key), str) or not raw.get(key).strip()
    ]
    if invalid:
        raise ConfigError(
            f"配置文件 {path} 的字段缺失或不是非空字符串：{', '.join(invalid)}"
        )

    context_window = raw.get("contextWindow")
    if not isinstance(context_window, int) or context_window <= 0:
        raise ConfigError(f"配置文件 {path} 的 contextWindow 必须是正整数。")

    return Config(
        base_url=raw["baseURL"].strip(),
        api_key=raw["apiKey"].strip(),
        model=raw["model"].strip(),
        context_window=context_window,
    )


def load_config(path: str | Path | None = None) -> Config:
    """加载并校验 provider.json 配置。

    优先使用显式传入的 path；否则按「当前目录 → 用户目录 ~/.powercode/」顺序
    查找第一个存在的 provider.json。

    provider.json 沿用原作者字段名（baseURL/apiKey/model，camelCase），
    这里映射为 Python 侧的 snake_case 字段。
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigError(
                f"找不到配置文件 {p}。请先复制 provider.json.example 为 provider.json 并填入你的 API Key。"
            )
        return _load(p)

    candidates = _candidate_paths()
    for candidate in candidates:
        if candidate.exists():
            return _load(candidate)

    searched = "\n".join(f"  - {p}" for p in candidates)
    raise ConfigError(
        "找不到配置文件 provider.json。请复制 provider.json.example 为 provider.json 并填入你的 API Key，放在以下任一位置：\n"
        + searched
    )
