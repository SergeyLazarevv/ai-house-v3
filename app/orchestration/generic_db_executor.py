from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.config import AppConfig
from app.domain.phone import normalize_phone_to_10
from app.mcp_servers.postgres_multi import run_multi_postgres_query
from app.orchestration.mcp_execution_policy import MCP_EXECUTION_POLICY_PROMPT
from app.orchestration.scenario_library import LoadedScenario
from app.shared.llm import build_llm

logger = logging.getLogger("app.scenario.db_executor")

_JSON_START = re.compile(r"\{[\s\S]*\}")


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s*```$", "", text).strip()
    i = text.find("{")
    if i < 0:
        return None
    candidate = text[i:].strip()
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")
        if open_braces > close_braces:
            try:
                obj = json.loads(candidate + ("}" * (open_braces - close_braces)))
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text[i:])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        m = _JSON_START.search(text)
        if not m:
            return None
        try:
            obj = json.loads(m.group())
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


def _max_rounds() -> int:
    try:
        return max(1, int((os.getenv("DB_EXECUTOR_MAX_ROUNDS") or "8").strip()))
    except ValueError:
        return 8


def _truncate(s: str, limit: int = 12000) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def _merge_postgres_targets(config: AppConfig) -> dict[str, str]:
    m = dict(config.postgres_targets.as_map())
    m.update(config.postgres_targets.auth_target_map())
    return m


def _apply_slot_placeholders(sql: str, expanded: dict[str, Any]) -> str:
    out = sql
    for key, value in expanded.items():
        if value is None:
            continue
        repl = str(value)
        out = (
            out.replace("{{" + key + "}}", repl)
            .replace("{{ " + key + " }}", repl)
        )
    return out


async def _run_single_db_step(
    *,
    target: str,
    sql: str,
    targets: dict[str, str],
    task: str,
    round_idx: int,
    max_rounds: int,
) -> dict[str, Any]:
    logger.info(
        "Исполнитель БД: раунд %s/%s target=%s sql_len=%s",
        round_idx,
        max_rounds,
        target,
        len(sql),
    )
    mcp_payload = await run_multi_postgres_query(
        sql=sql,
        targets={target: targets[target]},
        task=task,
    )
    try:
        mcp_parsed = json.loads(mcp_payload)
    except json.JSONDecodeError:
        mcp_parsed = {"raw": mcp_payload}
    return {
        "round": round_idx,
        "target": target,
        "sql": sql,
        "mcp": mcp_parsed,
    }


def _expand_slots_for_executor(slots: dict[str, Any], required: tuple[str, ...]) -> tuple[dict[str, Any] | None, str | None]:
    """Возвращает (expanded_slots, error_message)."""
    base: dict[str, Any] = {str(k): v for k, v in slots.items()}
    for key in required:
        v = base.get(key)
        if v is None or str(v).strip() == "":
            return None, f"Отсутствует обязательный слот: {key}"

    if "phone" in required:
        hint = str(base["phone"]).strip()
        phone10 = normalize_phone_to_10(hint)
        if not phone10:
            return None, "slots.phone не удалось нормализовать до 10 цифр (российский формат)."
        base["phone10"] = phone10
        base["phone11"] = f"7{phone10}"
        base["user_message_phone"] = f"8{phone10}"
    else:
        raw = base.get("phone")
        if raw is not None and str(raw).strip():
            phone10 = normalize_phone_to_10(str(raw).strip())
            if phone10:
                base["phone10"] = phone10
                base["phone11"] = f"7{phone10}"
                base["user_message_phone"] = f"8{phone10}"

    return base, None


def _executor_system_prompt(
    *,
    scenario: LoadedScenario,
    allowed_targets: list[str],
) -> str:
    targets_line = ", ".join(allowed_targets) if allowed_targets else "(нет настроенных DSN)"
    return (
        "Ты исполнитель шагов к PostgreSQL через MCP. Следуй тексту сценария ниже.\n"
        f"{MCP_EXECUTION_POLICY_PROMPT}\n\n"
        f"Доступные алиасы DSN (поле step.target): {targets_line}.\n"
        "После каждого результата запроса учитывай факты при планировании следующего шага "
        "(например: если пользователь заблокирован в auth, не запрашивай историю SMS).\n\n"
        "Отвечай ТОЛЬКО одним JSON без markdown и пояснений:\n"
        '- {"done": true} — если запросы к БД завершены;\n'
        '- {"step": {"target": "<алиас>", "sql": "<один SELECT или WITH или EXPLAIN>"}} — '
        "следующий запрос (один statement, без `;` внутри дополнительных команд).\n\n"
        "В sql можно использовать плейсхолдеры из словаря слотов (например {{phone10}}, {{phone11}}, "
        "{{user_message_phone}}) — они будут подставлены исполнителем.\n"
    )


async def run_markdown_scenario_db(
    *,
    scenario: LoadedScenario,
    task: str,
    config: AppConfig,
    slots: dict[str, Any],
) -> str:
    if not config.agent_db_enabled:
        return "Агент БД отключён (AGENT_DB_ENABLED=false)."

    targets = _merge_postgres_targets(config)
    if not targets:
        return "Postgres не настроен. Задайте POSTGRES_MCP_DSN_MAIN или POSTGRES_MCP_DSN."

    expanded, err = _expand_slots_for_executor(slots, scenario.required_slots)
    if err:
        return f"Запрос к БД не выполнен: {err}"
    assert expanded is not None

    allowed = sorted(targets.keys())
    llm = build_llm(config)
    system = _executor_system_prompt(scenario=scenario, allowed_targets=allowed)
    scenario_block = f"## Текст сценария «{scenario.scenario_id}»\n{scenario.body_markdown}"
    slots_json = json.dumps(expanded, ensure_ascii=False, indent=2)
    task_block = (task or "").strip() or "(пусто)"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system + "\n\n" + scenario_block},
        {
            "role": "user",
            "content": (
                f"Слоты (JSON):\n{slots_json}\n\n"
                f"Задача супервизора (task):\n{task_block}\n\n"
                "Верни JSON для первого шага или done, если шаги не нужны."
            ),
        },
    ]

    steps_executed: list[dict[str, Any]] = []
    max_r = _max_rounds()

    for round_idx in range(1, max_r + 1):
        raw = await llm.complete(messages)
        data = _extract_json_object(raw)
        if not data:
            payload = {
                "error": "Исполнитель БД вернул неразборчивый JSON",
                "raw_response": _truncate(raw, 2000),
                "steps_executed": steps_executed,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

        if data.get("done") is True:
            out = {"scenario_id": scenario.scenario_id, "steps_executed": steps_executed, "finished": True}
            return json.dumps(out, ensure_ascii=False, indent=2, default=str)

        step = data.get("step")
        if not isinstance(step, dict):
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "Нужен JSON с ключом done или step. Исправь ответ.",
                }
            )
            continue

        target = str(step.get("target") or "").strip()
        sql = str(step.get("sql") or "").strip()
        if not target or not sql:
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "В step нужны непустые target и sql. Исправь JSON.",
                }
            )
            continue

        if target not in targets:
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": f"Алиас «{target}» недоступен. Доступны: {allowed}. Исправь target.",
                }
            )
            continue

        sql_rendered = _apply_slot_placeholders(sql, expanded)
        record = await _run_single_db_step(
            target=target,
            sql=sql_rendered,
            targets=targets,
            task=task_block,
            round_idx=round_idx,
            max_rounds=max_r,
        )
        steps_executed.append(record)

        summary = _truncate(json.dumps(record["mcp"], ensure_ascii=False, default=str), 10000)
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Результат MCP (раунд {round_idx}, target={target}):\n{summary}\n\n"
                    "Если нужен ещё один запрос — верни JSON с step; иначе {{\"done\": true}}."
                ),
            }
        )

    payload = {
        "scenario_id": scenario.scenario_id,
        "steps_executed": steps_executed,
        "finished": False,
        "error": f"Достигнут лимит раундов ({max_r}). Увеличьте DB_EXECUTOR_MAX_ROUNDS при необходимости.",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
