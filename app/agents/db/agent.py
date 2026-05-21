from __future__ import annotations

from typing import Any

from app.config import AppConfig
from app.orchestration.scenario_registry import get_plugin


class DbInvestigationAgent:
    async def run(
        self,
        task: str,
        config: AppConfig,
        *,
        scenario: str | None = None,
        slots: dict[str, Any] | None = None,
    ) -> str:
        sid = (scenario or "").strip()
        if not sid:
            return (
                "Запрос к БД не выполнен: в ответе супервизора не указано поле scenario."
            )
        plugin = get_plugin(sid)
        if not plugin:
            return (
                f"Запрос к БД не выполнен: сценарий {sid!r} не зарегистрирован. "
                "Добавьте файл app/orchestration/scenarios/<id>.md с frontmatter scenario_id "
                "и настройте для него domain MCP executor."
            )
        return await plugin.run_db(task, config, slots or {}, scenario_id=sid)
