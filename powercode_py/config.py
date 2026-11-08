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


def load_config(path: str | Path = "provider.json") -> Config:
    """加载并校验 provider.json。

    provider.json 沿用原作者字段名（baseURL/apiKey/model，camelCase），
    这里映射为 Python 侧的 snake_case 字段。
    """
    p = Path(path)

    if not p.exists():
        raise ConfigError(
            f"找不到配置文件 {p}。请先复制 provider.json.example 为 provider.json 并填入你的 API Key。"
        )

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件 {p} 不是合法的 JSON：{exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"配置文件 {p} 顶层必须是 JSON 对象。")

    field_map = {
        "baseURL": "base_url",
        "apiKey": "api_key",
        "model": "model",
    }
    missing = [key for key in field_map if not raw.get(key)]
    if missing:
        raise ConfigError(f"配置文件 {p} 缺少字段：{', '.join(missing)}")

    return Config(
        base_url=raw["baseURL"].strip(),
        api_key=raw["apiKey"].strip(),
        model=raw["model"].strip(),
    )
