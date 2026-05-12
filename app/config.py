from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class PostgresTargets:
    main_dsn: str | None
    billing_dsn: str | None

    @classmethod
    def from_env(cls) -> "PostgresTargets":
        main = (
            os.getenv("POSTGRES_MCP_DSN_MAIN")
            or os.getenv("POSTGRES_MCP_DSN")
            or os.getenv("POSTGRES_URL")
            or ""
        ).strip() or None
        billing = (os.getenv("POSTGRES_MCP_DSN_BILLING") or "").strip() or None
        return cls(main_dsn=main, billing_dsn=billing)

    def as_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.main_dsn:
            out["main"] = self.main_dsn
        if self.billing_dsn:
            out["billing"] = self.billing_dsn
        return out


@dataclass
class AppConfig:
    yandex_api_key: str | None
    yandex_catalog_id: str | None
    yandex_model: str
    llm_provider: str
    graph_supervisor_max_steps: int
    agent_db_enabled: bool
    postgres_targets: PostgresTargets

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            yandex_api_key=os.getenv("YANDEX_API_KEY") or os.getenv("YANDEX_OAUTH"),
            yandex_catalog_id=os.getenv("YANDEX_CATALOG_ID"),
            yandex_model=(os.getenv("YANDEX_MODEL") or "yandexgpt-lite").strip(),
            llm_provider=(os.getenv("LLM_PROVIDER") or "yandex").strip().lower(),
            graph_supervisor_max_steps=max(1, int(os.getenv("GRAPH_SUPERVISOR_MAX_STEPS", "6"))),
            agent_db_enabled=_env_bool("AGENT_DB_ENABLED", True),
            postgres_targets=PostgresTargets.from_env(),
        )

    def llm_status(self) -> str:
        if self.llm_provider not in {"yandex", "yc", "yandexgpt"}:
            return f"unsupported provider: {self.llm_provider}"
        if self.yandex_api_key and self.yandex_catalog_id:
            return "ok"
        return "not configured"
