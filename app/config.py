from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class AppConfig:
    yandex_api_key: str | None
    yandex_catalog_id: str | None
    yandex_model: str
    llm_provider: str
    graph_supervisor_max_steps: int
    agent_db_enabled: bool
    mcp_auth_url: str
    mcp_sms_url: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            yandex_api_key=os.getenv("YANDEX_API_KEY") or os.getenv("YANDEX_OAUTH"),
            yandex_catalog_id=os.getenv("YANDEX_CATALOG_ID"),
            yandex_model=(os.getenv("YANDEX_MODEL") or "yandexgpt-lite").strip(),
            llm_provider=(os.getenv("LLM_PROVIDER") or "yandex").strip().lower(),
            graph_supervisor_max_steps=max(1, int(os.getenv("GRAPH_SUPERVISOR_MAX_STEPS", "6"))),
            agent_db_enabled=_env_bool("AGENT_DB_ENABLED", True),
            mcp_auth_url=(os.getenv("MCP_AUTH_URL") or "http://auth-mcp:8000/mcp").strip(),
            mcp_sms_url=(os.getenv("MCP_SMS_URL") or "http://sms-mcp:8000/mcp").strip(),
        )

    def llm_status(self) -> str:
        if self.llm_provider not in {"yandex", "yc", "yandexgpt"}:
            return f"unsupported provider: {self.llm_provider}"
        if self.yandex_api_key and self.yandex_catalog_id:
            return "ok"
        return "not configured"
