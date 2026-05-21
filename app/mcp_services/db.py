from __future__ import annotations

from datetime import date, datetime
import os
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg
from psycopg.rows import dict_row


def postgres_dsn() -> str:
    dsn = (os.getenv("POSTGRES_DSN") or "").strip()
    if not dsn:
        raise RuntimeError("POSTGRES_DSN is not configured")
    parsed = urlparse(dsn)
    query = [(key, value) for key, value in parse_qsl(parsed.query) if key != "uselibpqcompat"]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), parsed.fragment))


def query_timeout_seconds() -> int:
    raw = (os.getenv("DB_QUERY_TIMEOUT_SECONDS") or "5").strip()
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return 5


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def select_rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    timeout = query_timeout_seconds()
    with psycopg.connect(
        postgres_dsn(),
        connect_timeout=timeout,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {timeout * 1000}")
            cur.execute(sql, params)
            return [{key: _jsonable(value) for key, value in row.items()} for row in cur.fetchall()]
