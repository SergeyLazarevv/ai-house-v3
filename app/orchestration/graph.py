from __future__ import annotations

from app.agents.db.agent import DbInvestigationAgent
from app.config import AppConfig
from app.orchestration.prompts import build_synthesize_system_prompt
from app.orchestration.scenario_library import get_synthesis_system_prompt
from app.orchestration.state import GraphState
from app.orchestration.supervisor import node_supervisor
from app.shared.llm import build_llm


def _synthesis_system_prompt_for_state(state: GraphState) -> str:
    sid = (state.get("supervisor_scenario") or "").strip()
    if not sid:
        return build_synthesize_system_prompt()
    custom = get_synthesis_system_prompt(sid)
    return custom if custom else build_synthesize_system_prompt()


async def run_graph(user_message: str, config: AppConfig) -> str:
    state: GraphState = {"user_message": user_message, "agents_used": []}
    decision = await node_supervisor(state, config)
    state.update(decision)
    if state.get("supervisor_next") == "db":
        db_agent = DbInvestigationAgent()
        db_result = await db_agent.run(
            task=state.get("supervisor_task") or user_message,
            config=config,
            scenario=(state.get("supervisor_scenario") or "").strip() or None,
            slots=state.get("supervisor_slots") or {},
        )
        state["db_result"] = db_result
        state["agents_used"] = ["db"]
    synth_prompt = _synthesis_system_prompt_for_state(state)
    llm = build_llm(config)
    final = await llm.complete(
        [
            {"role": "system", "content": synth_prompt},
            {
                "role": "user",
                "content": (
                    f"Вопрос пользователя:\n{user_message}\n\n"
                    f"Результат БД:\n{state.get('db_result') or '(нет)'}"
                ),
            },
        ]
    )
    return final.strip()
