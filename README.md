# ai-house-v3

AI-агент для расследования SMS: Yandex Responses API + MCP (auth, sms).

По образцу [advanced-assistant](~/projects/advanced-assistant): один класс `Agent`, промпт в файле, инструменты из MCP.

## Структура

```
app/
  agent.py       — цикл agent → tool call → ответ (как advanced-assistant)
  prompt.md      — инструкции для модели (редактируете только это)
  mcp/           — клиент MCP + регистрация tools
  mcp_services/  — auth-mcp, sms-mcp (Postgres)
  main.py        — FastAPI
```

## Как работает

1. `list_tools()` на auth-mcp и sms-mcp → схемы параметров
2. Yandex Responses API получает промпт + tools
3. Модель сама вызывает tools и формирует ответ

## Запуск

```bash
docker compose up --build
```

- API: http://localhost:8030
- OpenWebUI: http://localhost:3010

## Настройка

`.env`:
- `LLM_PROVIDER` — `yandex` (по умолчанию) или `openai` (ChatGPT)
- Yandex: `YANDEX_API_KEY`, `YANDEX_CATALOG_ID`, `YANDEX_MODEL`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL` (опционально `OPENAI_BASE_URL` для Azure/прокси)
- MCP: `MCP_AUTH_URL`, `MCP_SMS_URL`

Поведение агента — в `app/prompt.md`.
