from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    user_message: str
    supervisor_next: str
    supervisor_task: str
    supervisor_scenario: str
    supervisor_slots: dict[str, Any]
    db_result: str
    final_response: str
    agents_used: list[str]
