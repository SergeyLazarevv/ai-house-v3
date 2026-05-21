from __future__ import annotations

from typing import Any

from app.config import AppConfig
from app.orchestration.scenario_library import get_loaded_scenario
from app.orchestration.sms_tool_executor import run_sms_delivery_tools


class GenericMarkdownScenarioPlugin:
    """
    Единый плагин для всех сценариев из markdown (см. app/orchestration/scenarios/).
    DB-шаги выполняются только через доменные MCP tools.
    """

    scenario_id = "__markdown__"

    async def run_db(
        self,
        task: str,
        config: AppConfig,
        slots: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> str:
        sid = (scenario_id or "").strip()
        sc = get_loaded_scenario(sid)
        if not sc:
            return (
                f"Запрос к БД не выполнен: сценарий {sid!r} не найден. "
                "Добавьте файл app/orchestration/scenarios/<id>.md с frontmatter scenario_id."
            )
        if sid == "sms_delivery":
            return await run_sms_delivery_tools(config=config, slots=slots)
        return f"Запрос к MCP не выполнен: для сценария {sid!r} не настроен domain tool executor."


generic_markdown_plugin = GenericMarkdownScenarioPlugin()
