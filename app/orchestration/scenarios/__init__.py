"""Обратная совместимость: сценарии загружаются из плагинов."""

from __future__ import annotations

import app.orchestration.plugins  # noqa: F401 — регистрация
from app.orchestration.plugins.registry import load_scenarios_text

__all__ = ["load_scenarios_text"]
