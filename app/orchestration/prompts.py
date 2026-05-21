from __future__ import annotations

from app.orchestration.scenario_registry import load_scenarios_text
from app.orchestration.state import GraphState


def summarize_state(state: GraphState) -> str:
    return f"Результат БД:\n{(state.get('db_result') or '(пусто)').strip()}"


def build_supervisor_system_prompt() -> str:
    scenarios = load_scenarios_text()
    base = (
        "Ты маршрутизатор (супервизор) ассистента расследований.\n"
        "Выбери один наиболее подходящий сценарий расследования из списка ниже и следуй ТОЛЬКО его правилам "
        "(шаги, обязательные слоты, когда выбирать db или finish).\n"
        "Допустимые значения next: db или finish.\n"
        "Выбирай db только если выбранный сценарий требует живых данных из БД и ты заполнил все слоты, "
        "которые сценарий требует на этом шаге.\n"
        "Не пиши SQL в task: доступ к данным выполняется только через domain MCP tools выбранного сценария.\n"
        "При обычном разговоре, определениях терминов или если сценарий не подходит — выбирай finish.\n"
        "Верни один JSON-объект с ключами: next, task, reason, scenario, slots.\n"
        "- scenario: строковый идентификатор из выбранного блока сценария (см. поле «Идентификатор» в каждом сценарии).\n"
        "- slots: объект; укажи только ключи, которые сценарий требует на текущем шаге (см. текст сценария). "
        "Используй {}, если next равен finish или сценарию пока не нужны слоты.\n"
    )
    if scenarios:
        base += "\nСценарии расследований:\n" + scenarios + "\n"
    base += (
        '\nСхема JSON: {"next":"db|finish","task":"...","reason":"...","scenario":"...","slots":{}}\n'
    )
    return base


def build_synthesize_system_prompt() -> str:
    return (
        "Сформируй краткий итоговый ответ на русском языке, опираясь только на переданные факты.\n"
        "Формат:\n"
        "1) Кратко\n"
        "2) Факты\n"
        "3) Что делать дальше\n"
    )
