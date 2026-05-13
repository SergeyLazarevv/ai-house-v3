from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.config import AppConfig


@runtime_checkable
class InvestigationScenarioPlugin(Protocol):
    """
    Контракт сценария: markdown для супервизора (или через scenario_library), опциональный промпт синтеза, шаг БД.
    Типичный сценарий описывается в app/orchestration/scenarios/<id>.md без отдельного класса на сценарий.
    """

    scenario_id: str

    def load_scenario_markdown(self) -> str:
        """Текст сценария для вставки в системный промпт супервизора."""
        ...

    def build_synthesis_system_prompt(self) -> str | None:
        """
        Системный промпт для финального ответа пользователю.
        Верни None, чтобы использовать общий `build_synthesize_system_prompt`.
        """
        ...

    async def run_db(
        self,
        task: str,
        config: AppConfig,
        slots: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> str:
        """Шаги read-only к БД по правилам сценария (или сообщение об ошибке/заглушке)."""
        ...
