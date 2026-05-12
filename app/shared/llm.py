from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx

from app.config import AppConfig


def _msg_text(m: dict[str, Any]) -> str:
    content = m.get("content")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _extract_yandex_text(payload: dict[str, Any]) -> str:
    result = payload.get("result") or {}
    alternatives = result.get("alternatives") or []
    for alt in alternatives:
        if not isinstance(alt, dict):
            continue
        message = alt.get("message") or {}
        if isinstance(message, dict) and isinstance(message.get("text"), str):
            return message["text"]
    return ""


@runtime_checkable
class LLM(Protocol):
    async def complete(self, messages: list[dict[str, Any]]) -> str: ...


class YandexLLM:
    def __init__(self, api_key: str, catalog_id: str, model: str):
        self._api_key = api_key
        self._catalog_id = catalog_id
        self._model = model
        self._url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    async def complete(self, messages: list[dict[str, Any]]) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self._url,
                headers={"Authorization": f"Api-Key {self._api_key}"},
                json={
                    "modelUri": f"gpt://{self._catalog_id}/{self._model}",
                    "completionOptions": {"stream": False},
                    "messages": [{"role": m.get("role", "user"), "text": _msg_text(m)} for m in messages],
                },
            )
            response.raise_for_status()
            return _extract_yandex_text(response.json()).strip()


def build_llm(config: AppConfig) -> LLM:
    provider = (config.llm_provider or "yandex").strip().lower()
    if provider in {"yandex", "yc", "yandexgpt"}:
        return YandexLLM(
            api_key=config.yandex_api_key or "",
            catalog_id=config.yandex_catalog_id or "",
            model=config.yandex_model,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER={provider!r}. Use yandex.")
