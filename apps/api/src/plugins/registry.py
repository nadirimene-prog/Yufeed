from typing import Dict, List

from src.plugins import BaseRiskPlugin

_registry: Dict[str, BaseRiskPlugin] = {}


def register_plugin(name: str, plugin: BaseRiskPlugin) -> None:
    _registry[name] = plugin


def get_plugin(name: str) -> BaseRiskPlugin | None:
    return _registry.get(name)


def list_plugins() -> List[str]:
    return sorted(_registry.keys())
