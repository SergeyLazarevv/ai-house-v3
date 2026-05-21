from __future__ import annotations

from app.orchestration.generic_markdown_plugin import GenericMarkdownScenarioPlugin
from app.orchestration.generic_markdown_plugin import generic_markdown_plugin
from app.orchestration.scenario_library import build_supervisor_scenarios_text, load_scenario_library


def get_plugin(scenario_id: str) -> GenericMarkdownScenarioPlugin | None:
    sid = (scenario_id or "").strip()
    if sid in load_scenario_library():
        return generic_markdown_plugin
    return None


def load_scenarios_text() -> str:
    """Тексты сценариев для супервизора: markdown из app/orchestration/scenarios/."""
    return build_supervisor_scenarios_text()
