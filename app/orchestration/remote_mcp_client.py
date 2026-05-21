from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _content_to_data(content: list[Any]) -> Any:
    parts: list[str] = []
    for chunk in content:
        text = getattr(chunk, "text", None)
        if isinstance(text, str):
            parts.append(text)
    raw = "\n".join(parts).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def call_remote_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with streamablehttp_client(url) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return {
                "ok": not bool(getattr(result, "isError", False)),
                "tool": tool_name,
                "response": _content_to_data(result.content),
            }
