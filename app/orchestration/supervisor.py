from __future__ import annotations

import json
from typing import Any

from app.config import AppConfig
from app.orchestration.prompts import build_supervisor_system_prompt, summarize_state
from app.orchestration.state import GraphState
from app.shared.llm import build_llm


def _extract_json(raw: str) -> dict:
    i = (raw or "").find("{")
    if i < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw[i:])
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        return {}
    return {}


def _parse_slots(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        out[str(key).strip()] = value
    return out


async def node_supervisor(state: GraphState, config: AppConfig) -> dict:
    llm = build_llm(config)
    prompt = (
        f"Вопрос:\n{state.get('user_message')}\n\n"
        f"Текущее состояние:\n{summarize_state(state)}\n"
    )
    raw = await llm.complete(
        [
            {"role": "system", "content": build_supervisor_system_prompt()},
            {"role": "user", "content": prompt},
        ]
    )
    data = _extract_json(raw)
    next_step = str(data.get("next", "finish")).strip().lower()
    if next_step not in {"db", "finish"}:
        next_step = "finish"
    scenario = str(data.get("scenario", "")).strip()
    slots = _parse_slots(data.get("slots"))
    return {
        "supervisor_next": next_step,
        "supervisor_task": str(data.get("task", "")).strip(),
        "supervisor_scenario": scenario,
        "supervisor_slots": slots,
    }
