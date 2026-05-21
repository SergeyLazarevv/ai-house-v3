from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel

from app.config import AppConfig
from app.logging_config import configure_logging
from app.orchestration.graph import run_graph

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
configure_logging()

app = FastAPI(
    title="ai-house-v3",
    description="Минимальный AI-ассистент для расследований",
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class OpenAIMessage(BaseModel):
    role: str
    content: Any = None


class OpenAIChatRequest(BaseModel):
    model: str | None = None
    messages: list[OpenAIMessage]
    stream: bool | None = False


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    config = AppConfig.from_env()
    return {
        "llm": config.llm_status(),
        "provider": config.llm_provider,
        "mcp": {
            "auth_url": config.mcp_auth_url,
            "sms_url": config.mcp_sms_url,
        },
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="поле message обязательно")
    config = AppConfig.from_env()
    response = await run_graph(message, config)
    return ChatResponse(response=response)


@app.get("/v1/models")
async def openai_models():
    return {
        "object": "list",
        "data": [{"id": "ai-house-v3-default", "object": "model", "created": int(time.time()), "owned_by": "ai-house-v3"}],
    }


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                parts.append(str(p.get("text") or p.get("content") or ""))
        return "\n".join(x for x in parts if x)
    return ""


@app.post("/v1/chat/completions")
async def openai_chat(req: OpenAIChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="поле messages обязательно")
    prompt = ""
    for m in req.messages[::-1]:
        if m.role == "user":
            prompt = _content_to_text(m.content).strip()
            if prompt:
                break
    if not prompt:
        prompt = "\n".join(_content_to_text(m.content) for m in req.messages).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="не удалось извлечь текст запроса")
    config = AppConfig.from_env()
    answer = await run_graph(prompt, config)

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = req.model or "ai-house-v3-default"
    if req.stream:
        async def _events():
            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': answer}, 'finish_reason': None}]})}\n\n"
            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_events(), media_type="text/event-stream")

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
