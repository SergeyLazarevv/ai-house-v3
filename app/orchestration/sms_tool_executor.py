from __future__ import annotations

import json
import os
import re
from typing import Any

from app.config import AppConfig
from app.domain.phone import normalize_phone_to_10
from app.orchestration.remote_mcp_client import call_remote_tool
from app.shared.llm import build_llm


_JSON_OBJECT = re.compile(r"\{[\s\S]*\}")
_FENCED_JSON = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    match = _FENCED_JSON.search(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s*```$", "", text).strip()
    return text


def _balance_json_braces(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return text
    fragment = text[start:]
    depth = 0
    in_string = False
    escape = False
    for ch in fragment:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    if depth > 0:
        fragment += "}" * depth
    return fragment


def _json_candidates(raw: str) -> list[str]:
    text = _strip_code_fence(raw)
    candidates = [text]
    balanced = _balance_json_braces(text)
    if balanced != text:
        candidates.append(balanced)
    match = _JSON_OBJECT.search(text)
    if match:
        fragment = match.group()
        candidates.extend([fragment, _balance_json_braces(fragment)])
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    for candidate in _json_candidates(raw):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _max_tool_rounds() -> int:
    try:
        return max(1, int((os.getenv("MCP_TOOL_PLANNER_MAX_ROUNDS") or "5").strip()))
    except ValueError:
        return 5


def _allowed_tools(config: AppConfig) -> dict[tuple[str, str], str]:
    return {
        ("auth", "get_user_by_phone"): config.mcp_auth_url,
        ("auth", "get_user_activity_by_phone"): config.mcp_auth_url,
        ("sms", "get_recent_sms_by_phone"): config.mcp_sms_url,
    }


def _planner_system_prompt() -> str:
    return """
Ты планировщик read-only MCP tools для сценария проверки SMS.

Доступные tools:
- auth.get_user_activity_by_phone(phone: string): проверяет активность пользователя.
- auth.get_user_by_phone(phone: string): возвращает найденных пользователей auth.
- sms.get_recent_sms_by_phone(phone: string, limit: integer): возвращает историю отправленных SMS.

Правила:
- Выбирай только tools из списка выше.
- Не пиши SQL и не выдумывай имена tools.
- Обычно нужно проверить активность пользователя и историю SMS.
- Даже если пользователь неактивен, историю SMS всё равно можно запросить: нужны сообщения, отправленные до блокировки.
- Не вызывай один и тот же tool с теми же args повторно.
- Когда фактов достаточно, верни done=true.

Отвечай только JSON:
{"tool_call":{"server":"auth|sms","tool":"<tool_name>","args":{...}}}
или
{"done":true}
""".strip()


async def run_sms_delivery_tools(
    *,
    config: AppConfig,
    slots: dict[str, Any],
) -> str:
    raw_phone = str(slots.get("phone") or "").strip()
    phone10 = normalize_phone_to_10(raw_phone)
    if not phone10:
        return "Запрос к MCP не выполнен: slots.phone не удалось нормализовать до 10 цифр."

    phone = f"8{phone10}"
    allowed_tools = _allowed_tools(config)
    tool_results: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _planner_system_prompt()},
        {
            "role": "user",
            "content": (
                f"Сценарий: sms_delivery\n"
                f"Слоты: {json.dumps({'phone': phone, 'phone10': phone10}, ensure_ascii=False)}\n"
                "Выбери первый MCP tool."
            ),
        },
    ]
    llm = build_llm(config)
    seen_calls: set[str] = set()

    for round_idx in range(1, _max_tool_rounds() + 1):
        raw = await llm.complete(messages)
        plan = _extract_json_object(raw)
        if not plan:
            if round_idx < _max_tool_rounds():
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Ответ должен быть валидным JSON-объектом без markdown и пояснений. "
                            'Верни {"tool_call":{...}} или {"done":true}.'
                        ),
                    }
                )
                continue
            return json.dumps(
                {
                    "scenario_id": "sms_delivery",
                    "tool_results": tool_results,
                    "finished": False,
                    "error_kind": "planner",
                    "error": "MCP tool planner не смог выбрать tool: вернул неразборчивый JSON",
                    "raw_response": raw,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        if plan.get("done") is True:
            break

        tool_call = plan.get("tool_call")
        if not isinstance(tool_call, dict):
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": "Нужен JSON с tool_call или done=true."})
            continue

        server = str(tool_call.get("server") or "").strip()
        tool_name = str(tool_call.get("tool") or "").strip()
        args = tool_call.get("args")
        if not isinstance(args, dict):
            args = {}
        if server not in {"auth", "sms"} or (server, tool_name) not in allowed_tools:
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool запрещён. Доступны: {sorted(f'{s}.{t}' for s, t in allowed_tools)}.",
                }
            )
            continue

        args = dict(args)
        args["phone"] = phone
        if tool_name == "get_recent_sms_by_phone":
            args["limit"] = min(max(int(args.get("limit") or 5), 1), 20)
        call_key = json.dumps({"server": server, "tool": tool_name, "args": args}, sort_keys=True, ensure_ascii=False)
        if call_key in seen_calls:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": "Этот tool с такими args уже вызывался. Выбери другой tool или done=true."})
            continue
        seen_calls.add(call_key)

        result = await call_remote_tool(allowed_tools[(server, tool_name)], tool_name, args)
        record = {
            "round": round_idx,
            "server": server,
            "tool": tool_name,
            "args": args,
            "result": result,
        }
        tool_results.append(record)
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Результат tool call:\n{json.dumps(record, ensure_ascii=False, default=str)}\n\n"
                    "Если нужен ещё один MCP tool — верни tool_call. Если фактов достаточно — верни {\"done\":true}."
                ),
            }
        )

    return json.dumps(
        {
            "scenario_id": "sms_delivery",
            "tool_results": tool_results,
            "finished": True,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )
