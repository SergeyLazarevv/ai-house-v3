from __future__ import annotations

from app.orchestration.plugins.registry import register_plugin
from app.orchestration.plugins.test_investigation.plugin import test_investigation_plugin

register_plugin(test_investigation_plugin)

__all__ = ["test_investigation_plugin"]
