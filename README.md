# ai-house-v3

Минимальный AI-агент для расследований с Yandex AI, несколькими Postgres-источниками и OpenWebUI.

## Что внутри

- FastAPI API: `/api/chat`, `/api/health`, `/api/status`
- OpenAI-совместимый API: `/v1/models`, `/v1/chat/completions`
- Базовый сценарий расследования: `app/orchestration/scenarios/test_investigation.md` (TOML frontmatter `+++` … `+++`, см. также `sms_delivery.md`)
- DB-агент с MCP-подключением к нескольким Postgres источникам
- OpenWebUI, подключенный к локальному API
- Сертификаты в Docker (CA bundle + env + volume)

## Запуск одной командой

```bash
docker compose up -d --build
```

## Адреса

- API: [http://localhost:8030](http://localhost:8030)
- Swagger: [http://localhost:8030/docs](http://localhost:8030/docs)
- OpenWebUI: [http://localhost:3010](http://localhost:3010)

## Быстрый smoke-check

```bash
curl -s http://localhost:8030/api/health
curl -s http://localhost:8030/api/status
curl -s -X POST http://localhost:8030/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Проведи тестовое расследование по user_id=123"}'
```

## Переменные окружения

См. `.env.example`. В локальном `.env` уже проставлены реальные `YANDEX_*` из `ai-house`, как было запрошено.

Для Postgres используется MCP-схема как в LogsAi:
- агент поднимает `npx @modelcontextprotocol/server-postgres <DSN>` для каждого источника;
- вызов SQL идёт через MCP tool (`query`).
