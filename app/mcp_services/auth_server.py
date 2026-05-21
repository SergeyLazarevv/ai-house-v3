from __future__ import annotations

import os
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_services.db import select_rows


mcp = FastMCP(
    "auth-mcp",
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


def _phone_variants(phone: str) -> tuple[str, str, str]:
    phone10 = _normalize_phone_to_10(phone)
    if not phone10:
        raise ValueError("phone must be a Russian phone number in 10/11 digit format")
    return phone10, f"7{phone10}", f"8{phone10}"


@mcp.tool()
def get_user_by_phone(phone: str) -> dict[str, Any]:
    """Return auth user rows matching a phone number."""
    phone10, phone11, phone8 = _phone_variants(phone)
    rows = select_rows(
        """
SELECT
  u.id::text AS id,
  u.phone,
  u.email,
  u.is_active,
  u.updated_at
FROM public.users u
WHERE u.phone IN (%s, %s, %s)
   OR regexp_replace(COALESCE(u.phone, ''), '[^0-9]', '', 'g') IN (%s, %s, %s)
ORDER BY u.updated_at DESC NULLS LAST
LIMIT 10
""".strip(),
        (phone10, phone11, phone8, phone10, phone11, phone8),
    )
    return {"phone": phone, "users": rows}


@mcp.tool()
def get_user_activity_by_phone(phone: str) -> dict[str, Any]:
    """Return the current activity flag for the best matching auth user."""
    payload = get_user_by_phone(phone)
    users = payload["users"]
    if not users:
        return {"phone": phone, "found": False, "is_active": None, "user": None}
    user = users[0]
    return {
        "phone": phone,
        "found": True,
        "is_active": user.get("is_active"),
        "user": user,
    }


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
