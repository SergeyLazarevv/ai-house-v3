from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import AppConfig
from app.llm.client import build_llm_client, load_instructions, model_uri
from app.mcp.registry import as_function_tools, discover_mcp_tools, run_tool, tool_map


def _max_rounds() -> int:
    try:
        return max(1, int((os.getenv("AGENT_MAX_ROUNDS") or "8").strip()))
    except ValueError:
        return 8


def _runtime_context() -> str:
    now = datetime.now(timezone(timedelta(hours=3)))
    return f"Текущие дата и время (Europe/Moscow): {now.isoformat(timespec='seconds')}"


class Agent:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = build_llm_client(config)
        self._sessions: dict[str, dict[str, Any]] = {}

    async def run(self, message: str, session_id: str = "default") -> str:
        tools = await discover_mcp_tools(self._config)
        if not tools:
            return "MCP-инструменты недоступны."

        index = tool_map(tools)
        function_tools = as_function_tools(tools)
        instructions = f"{load_instructions()}\n\n{_runtime_context()}"

        session = self._sessions.setdefault(session_id, {"last_response_id": None})
        response = await asyncio.to_thread(
            self._client.responses.create,
            model=model_uri(self._config),
            store=True,
            tools=function_tools,
            tool_choice="auto",
            instructions=instructions,
            previous_response_id=session["last_response_id"],
            input=message,
        )

        for _ in range(_max_rounds()):
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            outputs: list[dict[str, Any]] = []
            for call in function_calls:
                tool = index.get(call.name)
                if tool is None:
                    payload = json.dumps({"error": f"unknown tool {call.name}"}, ensure_ascii=False)
                else:
                    args = json.loads(call.arguments or "{}")
                    payload = await run_tool(tool, args)
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": payload,
                    }
                )

            response = await asyncio.to_thread(
                self._client.responses.create,
                model=model_uri(self._config),
                store=True,
                tools=function_tools,
                previous_response_id=response.id,
                input=outputs,
            )

        session["last_response_id"] = response.id
        return (response.output_text or "").strip()
