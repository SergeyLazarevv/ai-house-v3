from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.config import AppConfig


@runtime_checkable
class InvestigationScenarioPlugin(Protocol):
    """
    Плагин сценария расследования: markdown для супервизора, опциональный промпт синтеза, выполнение шага БД.
    Новые сценарии добавляют класс с тем же контрактом и регистрируют в registry.
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
    ) -> str:
        """Один шаг read-only к БД по правилам сценария (или сообщение об ошибке/заглушке)."""
        ...
