from __future__ import annotations

from app.orchestration.plugins.protocol import InvestigationScenarioPlugin
from app.orchestration.plugins.registry import (
    get_plugin,
    iter_plugins,
    load_scenarios_text,
    register_plugin,
)

# Регистрация markdown-сценариев через scenario_library при первом обращении;
# legacy register_plugin остаётся для редких исключений.
import app.orchestration.plugins.registry as _registry  # noqa: F401, E402

__all__ = [
    "InvestigationScenarioPlugin",
    "get_plugin",
    "iter_plugins",
    "load_scenarios_text",
    "register_plugin",
]
