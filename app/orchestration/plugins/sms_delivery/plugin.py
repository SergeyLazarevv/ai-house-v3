from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from app.config import AppConfig
from app.domain.phone import normalize_phone_to_10
from app.mcp_servers.postgres_multi import run_multi_postgres_query
from app.repositories.sms_repository import SmsRepository


class _QueryExecutor(Protocol):
    async def execute(self, sql: str, targets: dict[str, str], task: str) -> str: ...


class _McpExecutor:
    async def execute(self, sql: str, targets: dict[str, str], task: str) -> str:
        return await run_multi_postgres_query(sql=sql, targets=targets, task=task)


class SmsDeliveryPlugin:
    scenario_id = "sms_delivery"

    def __init__(
        self,
        sms_repository: SmsRepository | None = None,
        query_executor: _QueryExecutor | None = None,
    ) -> None:
        self._sms_repository = sms_repository or SmsRepository()
        self._query_executor = query_executor or _McpExecutor()

    def load_scenario_markdown(self) -> str:
        return (Path(__file__).resolve().parent / "scenario.md").read_text(encoding="utf-8")

    def build_synthesis_system_prompt(self) -> str | None:
        return (
            "Сформируй ответ на русском языке, используя только факты из результата БД.\n"
            "Это ответ по сценарию доставки SMS. Строго соблюдай формат:\n"
            "Для пользователя с номером N найдены следующие смс:\n"
            "- дата отправки: ...\n"
            "- текст смс: ...\n"
            "- статус доставки: ...\n"
            "- оператор: ...\n"
            "- ошибка: ...   (эту строку включай только если error_text не пустой)\n\n"
            "- дата отправки: ...\n"
            "- текст смс: ...\n"
            "- статус доставки: ...\n"
            "- оператор: ...\n"
            "- ошибка: ...   (эту строку включай только если error_text не пустой)\n"
            "\n"
            "Между блоками разных SMS вставляй одну пустую строку.\n"
            "Если operator_type и operator_name пусты, выведи: «- оператор: (не указано)».\n"
            "Повтори структуру для всех возвращённых строк (не больше 5).\n"
            "Если строк нет, выведи: «В истории оповещений пользователя не найдено отправленных смс по указанному номеру.»\n"
        )

    async def run_db(
        self,
        task: str,
        config: AppConfig,
        slots: dict[str, Any],
    ) -> str:
        if not config.agent_db_enabled:
            return "Агент БД отключён (AGENT_DB_ENABLED=false)."
        targets = config.postgres_targets.as_map()
        if not targets:
            return (
                "Postgres не настроен. Задайте POSTGRES_MCP_DSN_MAIN или POSTGRES_MCP_DSN."
            )
        phone_raw = slots.get("phone")
        phone_hint = str(phone_raw).strip() if phone_raw is not None else ""
        if not phone_hint:
            return (
                "Запрос к БД не выполнен: для сценария sms_delivery в slots отсутствует или пустое поле phone. "
                "Супервизор должен заполнить slots по сценарию; при неясности — finish."
            )
        phone_number = normalize_phone_to_10(phone_hint)
        if not phone_number:
            return (
                "Запрос к БД не выполнен: slots.phone не удалось нормализовать до 10 цифр "
                "(ожидается российский формат: 10 цифр или 11 с ведущей 7/8)."
            )
        sql_from_task = self._sms_repository.extract_sql_from_task(task)
        sql = (
            self._sms_repository.render_sql_with_phone(sql_from_task, phone_number)
            if sql_from_task
            else self._sms_repository.default_recent_sms_sql(phone_number)
        )
        return await self._query_executor.execute(sql=sql, targets=targets, task=task)


sms_delivery_plugin = SmsDeliveryPlugin()
