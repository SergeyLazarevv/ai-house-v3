from __future__ import annotations

from app.orchestration.plugins.protocol import InvestigationScenarioPlugin
from app.orchestration.plugins.registry import (
    get_plugin,
    iter_plugins,
    load_scenarios_text,
    register_plugin,
)

# Регистрация плагинов при импорте пакета
import app.orchestration.plugins.sms_delivery as _sms_delivery  # noqa: F401, E402
import app.orchestration.plugins.test_investigation as _test_investigation  # noqa: F401, E402

__all__ = [
    "InvestigationScenarioPlugin",
    "get_plugin",
    "iter_plugins",
    "load_scenarios_text",
    "register_plugin",
]
