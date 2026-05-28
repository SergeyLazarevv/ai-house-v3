from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from app.config import AppConfig

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompt.md"
_YANDEX_RESPONSES_URL = "https://rest-assistant.api.cloud.yandex.net/v1"


def build_llm_client(config: AppConfig) -> OpenAI:
    if config.llm_provider == "openai":
        kwargs: dict[str, str] = {"api_key": config.openai_api_key or ""}
        if config.openai_base_url:
            kwargs["base_url"] = config.openai_base_url
        return OpenAI(**kwargs)

    return OpenAI(
        base_url=_YANDEX_RESPONSES_URL,
        api_key=config.yandex_api_key or "",
        project=config.yandex_catalog_id or "",
    )


def model_uri(config: AppConfig) -> str:
    if config.llm_provider == "openai":
        return config.openai_model

    model = config.yandex_model
    if model.startswith("gpt://"):
        return model
    return f"gpt://{config.yandex_catalog_id}/{model}"


def load_instructions() -> str:
    if not _PROMPT_PATH.is_file():
        return "Ты ассистент поддержки."
    if os.getenv("APP_RELOAD") == "1":
        return _PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _read_instructions_cached()


@lru_cache
def _read_instructions_cached() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()
