"""Config loader — reads YAML configuration files relative to this module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).parent


def load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the config directory."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {filename} must be a YAML mapping")
    return data


def load_model_routing() -> dict[str, Any]:
    return load_yaml("model_routing.yaml")


def load_budgets() -> dict[str, Any]:
    return load_yaml("budgets.yaml")


__all__ = ["load_yaml", "load_model_routing", "load_budgets"]
