from __future__ import annotations

from app.orchestration.plugins.protocol import InvestigationScenarioPlugin

_PLUGINS: dict[str, InvestigationScenarioPlugin] = {}


def register_plugin(plugin: InvestigationScenarioPlugin) -> None:
    sid = plugin.scenario_id
    if sid in _PLUGINS:
        raise ValueError(f"Сценарий {sid!r} уже зарегистрирован")
    _PLUGINS[sid] = plugin


def get_plugin(scenario_id: str) -> InvestigationScenarioPlugin | None:
    return _PLUGINS.get((scenario_id or "").strip())


def iter_plugins() -> list[InvestigationScenarioPlugin]:
    return sorted(_PLUGINS.values(), key=lambda p: p.scenario_id)


def load_scenarios_text() -> str:
    """Склеивает markdown всех зарегистрированных плагинов для супервизора."""
    parts: list[str] = []
    for plugin in iter_plugins():
        text = plugin.load_scenario_markdown().strip()
        if text:
            parts.append(f"### {plugin.scenario_id}\n{text}")
    return "\n\n".join(parts).strip()
