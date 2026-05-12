from __future__ import annotations

import re


def normalize_phone_to_10(raw: str) -> str | None:
    """
    Convert a single phone string (as given by the supervisor in JSON `phone`) to 10 national digits.
    Does not scan free-form ticket text — that is the model's job.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw.strip())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return digits[1:]
    if len(digits) == 10:
        return digits
    return None
