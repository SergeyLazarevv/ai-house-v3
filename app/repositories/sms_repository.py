from __future__ import annotations

import re


class SmsRepository:
    def extract_sql_from_task(self, task: str) -> str | None:
        if not task:
            return None
        match = re.search(r"```(?:sql)?\s*(.*?)```", task, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        sql = (match.group(1) or "").strip()
        return sql or None

    def render_sql_with_phone(self, sql_template: str, phone10: str) -> str:
        sql = (sql_template or "").strip()
        if not sql:
            return self.default_recent_sms_sql(phone10)
        return (
            sql.replace("{{phone10}}", phone10)
            .replace("{phone10}", phone10)
            .replace("{{phone_number}}", phone10)
            .replace("{phone_number}", phone10)
        )

    def default_recent_sms_sql(self, phone10: str) -> str:
        return f"""
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
WHERE regexp_replace(ss.phone_number, '[^0-9]', '', 'g') LIKE '%{phone10}'
ORDER BY COALESCE(ss.sending_date, ss.received_date) DESC
LIMIT 5
""".strip()
