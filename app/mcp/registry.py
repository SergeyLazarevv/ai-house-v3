from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.config import AppConfig
from app.mcp.remote import call_remote_tool, list_remote_tools


@dataclass(frozen=True)
class McpTool:
    server: str
    url: str
    name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def api_name(self) -> str:
        return f"{self.server}__{self.name}"


async def discover_mcp_tools(config: AppConfig) -> list[McpTool]:
    out: list[McpTool] = []
    for server, url in config.mcp_servers():
        for tool in await list_remote_tools(url):
            out.append(
                McpTool(
                    server=server,
                    url=url,
                    name=str(tool["name"]),
                    description=str(tool.get("description") or ""),
                    input_schema=dict(tool.get("input_schema") or {}),
                )
            )
    return out


def as_function_tools(tools: list[McpTool]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": tool.api_name,
            "description": tool.description or f"MCP {tool.server}.{tool.name}",
            "parameters": tool.input_schema or {"type": "object", "properties": {}},
        }
        for tool in tools
    ]


def tool_map(tools: list[McpTool]) -> dict[str, McpTool]:
    return {tool.api_name: tool for tool in tools}


async def run_tool(tool: McpTool, arguments: dict[str, Any]) -> str:
    result = await call_remote_tool(tool.url, tool.name, arguments)
    return json.dumps(result, ensure_ascii=False, default=str)
