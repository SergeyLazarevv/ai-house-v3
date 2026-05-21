from __future__ import annotations

import os
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_services.db import select_rows


mcp = FastMCP(
    "sms-mcp",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)


def _normalize_phone_to_10(raw: str) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw.strip())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return digits[1:]
    if len(digits) == 10:
        return digits
    return None


@mcp.tool()
def get_recent_sms_by_phone(phone: str, limit: int = 5) -> dict[str, Any]:
    """Return recent SMS delivery records for a phone number."""
    phone10 = _normalize_phone_to_10(phone)
    if not phone10:
        raise ValueError("phone must be a Russian phone number in 10/11 digit format")
    safe_limit = min(max(int(limit), 1), 20)
    rows = select_rows(
        """
SELECT
  ss.phone_number,
  ss.received_date,
  ss.sending_date,
  ss.sms_text,
  ss.result,
  ss.error_text,
  oa.sender_name,
  op.type AS operator_type,
  op.name AS operator_name
FROM send_sms ss
LEFT JOIN operator_accounts oa ON ss.account_id = oa.id
LEFT JOIN operators op ON op.id = oa.operator_id
WHERE regexp_replace(ss.phone_number, '[^0-9]', '', 'g') LIKE %s
ORDER BY COALESCE(ss.sending_date, ss.received_date) DESC
LIMIT %s
""".strip(),
        (f"%{phone10}", safe_limit),
    )
    return {"phone": phone, "phone10": phone10, "sms": rows}


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
