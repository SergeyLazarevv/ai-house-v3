from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import os
import re
import shutil
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _is_read_only_sql(sql: str) -> bool:
    text = (sql or "").strip()
    if not text:
        return False
    # Reject multiple statements.
    if ";" in text.rstrip(";"):
        return False
    if not re.match(r"(?is)^\s*(select|with|explain)\b", text):
        return False
    forbidden = re.search(
        r"(?is)\b(insert|update|delete|merge|create|alter|drop|truncate|grant|revoke|"
        r"vacuum|copy|call|do|prepare|execute|set)\b",
        text,
    )
    return not bool(forbidden)


def _pick_query_tool(tools: list[Any]) -> str | None:
    preferred = ("query", "postgres_query", "execute_query")
    names = [getattr(t, "name", "") for t in tools]
    for p in preferred:
        if p in names:
            return p
    return names[0] if names else None


def _mcp_content_to_text(content: list[Any]) -> str:
    parts: list[str] = []
    for chunk in content:
        text = getattr(chunk, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts).strip()


def _query_timeout_seconds() -> float:
    raw = (os.getenv("DB_QUERY_TIMEOUT_SECONDS") or "5").strip()
    try:
        return max(0.1, float(raw))
    except ValueError:
        return 5.0


async def _query_one_via_mcp(alias: str, dsn: str, sql: str, timeout: float) -> dict[str, Any]:
    command = "npx"
    args = ["-y", "@modelcontextprotocol/server-postgres", dsn.strip()]
    if shutil.which("timeout"):
        command = "timeout"
        args = ["--kill-after=1s", f"{timeout:g}s", "npx", *args]

    params = StdioServerParameters(command=command, args=args, env=None)
    try:
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            tools_result = await session.list_tools()
            tool_name = _pick_query_tool(list(tools_result.tools))
            if not tool_name:
                return {
                    "alias": alias,
                    "ok": False,
                    "error": "Сервер @modelcontextprotocol/server-postgres не предоставил инструментов",
                }
            call_result = await session.call_tool(tool_name, {"sql": sql})
            text = _mcp_content_to_text(call_result.content)
            return {
                "alias": alias,
                "ok": not bool(getattr(call_result, "isError", False)),
                "tool": tool_name,
                "response": text,
            }
    except FileNotFoundError as exc:
        return {
            "alias": alias,
            "ok": False,
            "error": f"npx не установлен: {exc!s}",
        }
    except Exception as exc:  # pragma: no cover
        return {"alias": alias, "ok": False, "error": str(exc)}


async def _query_one_with_timeout(alias: str, dsn: str, sql: str, timeout: float) -> dict[str, Any]:
    started = asyncio.get_running_loop().time()
    try:
        result = await asyncio.wait_for(
            _query_one_via_mcp(alias, dsn, sql, timeout),
            timeout=timeout + 2,
        )
        elapsed = asyncio.get_running_loop().time() - started
        if result.get("ok") is False and elapsed >= timeout:
            result["error"] = f"Запрос к БД превысил таймаут {timeout:g} секунд"
        return result
    except TimeoutError:
        return {
            "alias": alias,
            "ok": False,
            "error": f"Запрос к БД превысил таймаут {timeout:g} секунд",
        }


async def run_multi_postgres_query(sql: str, targets: dict[str, str], task: str) -> str:
    if not _is_read_only_sql(sql):
        payload = {
            "task": task,
            "sql": sql,
            "targets": list(targets.keys()),
            "results": [
                {
                    "alias": alias,
                    "ok": False,
                    "error": "Запрос отклонён: разрешены только читающие SELECT / WITH / EXPLAIN",
                }
                for alias in targets.keys()
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    timeout = _query_timeout_seconds()
    jobs = [_query_one_with_timeout(alias, dsn, sql, timeout) for alias, dsn in targets.items()]
    results = await asyncio.gather(*jobs)
    payload = {"task": task, "sql": sql, "targets": list(targets.keys()), "results": results}
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
