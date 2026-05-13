from __future__ import annotations

from typing import Any

from app.config import AppConfig
from app.orchestration.generic_db_executor import run_markdown_scenario_db
from app.orchestration.scenario_library import get_loaded_scenario


class GenericMarkdownScenarioPlugin:
    """
    Единый плагин для всех сценариев из markdown (см. app/orchestration/scenarios/).
    Реализация run_db делегирует промпт-only исполнителю.
    """

    scenario_id = "__markdown__"

    def load_scenario_markdown(self) -> str:
        return ""

    def build_synthesis_system_prompt(self) -> str | None:
        return None

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
        return await run_markdown_scenario_db(
            scenario=sc,
            task=task,
            config=config,
            slots=slots,
        )


generic_markdown_plugin = GenericMarkdownScenarioPlugin()
