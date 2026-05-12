from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import AppConfig


class TestInvestigationPlugin:
    scenario_id = "test_investigation"

    def load_scenario_markdown(self) -> str:
        return (Path(__file__).resolve().parent / "scenario.md").read_text(encoding="utf-8")

    def build_synthesis_system_prompt(self) -> str | None:
        # Общий формат ответа — как у дефолтного синтеза
        return None

    async def run_db(
        self,
        task: str,
        config: AppConfig,
        slots: dict[str, Any],
    ) -> str:
        return (
            "Запрос к БД не выполнен: сценарий test_investigation пока не реализован в плагине "
            "(добавьте SQL и вызов MCP к нужному DSN в методе run_db)."
        )


test_investigation_plugin = TestInvestigationPlugin()
