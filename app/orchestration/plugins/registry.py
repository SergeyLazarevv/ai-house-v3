from __future__ import annotations

from app.orchestration.generic_markdown_plugin import generic_markdown_plugin
from app.orchestration.plugins.protocol import InvestigationScenarioPlugin
from app.orchestration.scenario_library import build_supervisor_scenarios_text, load_scenario_library

_PLUGINS: dict[str, InvestigationScenarioPlugin] = {}


def register_plugin(plugin: InvestigationScenarioPlugin) -> None:
    sid = plugin.scenario_id
    if sid in _PLUGINS:
        raise ValueError(f"Сценарий {sid!r} уже зарегистрирован")
    _PLUGINS[sid] = plugin


def get_plugin(scenario_id: str) -> InvestigationScenarioPlugin | None:
    sid = (scenario_id or "").strip()
    if sid in load_scenario_library():
        return generic_markdown_plugin
    return _PLUGINS.get(sid)


def iter_plugins() -> list[InvestigationScenarioPlugin]:
    """Только legacy-плагины, зарегистрированные через register_plugin (markdown — в scenario_library)."""
    return sorted(_PLUGINS.values(), key=lambda p: p.scenario_id)


def load_scenarios_text() -> str:
    """Тексты сценариев для супервизора: markdown из app/orchestration/scenarios/."""
    return build_supervisor_scenarios_text()
