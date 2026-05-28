from __future__ import annotations

import os
from dataclasses import dataclass


def normalize_llm_provider(raw: str | None) -> str:
    value = (raw or "yandex").strip().lower()
    if value in {"yandex", "yc", "yandexgpt"}:
        return "yandex"
    if value in {"openai", "chatgpt", "gpt"}:
        return "openai"
    return value


@dataclass
class AppConfig:
    llm_provider: str
    yandex_api_key: str | None
    yandex_catalog_id: str | None
    yandex_model: str
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    mcp_auth_url: str
    mcp_sms_url: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            llm_provider=normalize_llm_provider(os.getenv("LLM_PROVIDER")),
            yandex_api_key=os.getenv("YANDEX_API_KEY") or os.getenv("YANDEX_OAUTH"),
            yandex_catalog_id=os.getenv("YANDEX_CATALOG_ID"),
            yandex_model=(os.getenv("YANDEX_MODEL") or "yandexgpt/rc").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=(os.getenv("OPENAI_MODEL") or "gpt-4o").strip(),
            openai_base_url=(os.getenv("OPENAI_BASE_URL") or "").strip() or None,
            mcp_auth_url=(os.getenv("MCP_AUTH_URL") or "http://auth-mcp:8000/mcp").strip(),
            mcp_sms_url=(os.getenv("MCP_SMS_URL") or "http://sms-mcp:8000/mcp").strip(),
        )

    def mcp_servers(self) -> list[tuple[str, str]]:
        return [
            ("auth", self.mcp_auth_url),
            ("sms", self.mcp_sms_url),
        ]

    def llm_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_model
        return self.yandex_model

    def llm_status(self) -> str:
        if self.llm_provider == "yandex":
            if self.yandex_api_key and self.yandex_catalog_id:
                return "ok"
            return "not configured"
        if self.llm_provider == "openai":
            if self.openai_api_key:
                return "ok"
            return "not configured"
        return f"unsupported provider: {self.llm_provider}"
