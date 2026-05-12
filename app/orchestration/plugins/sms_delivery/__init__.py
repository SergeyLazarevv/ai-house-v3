from __future__ import annotations

from app.orchestration.plugins.registry import register_plugin
from app.orchestration.plugins.sms_delivery.plugin import sms_delivery_plugin

register_plugin(sms_delivery_plugin)

__all__ = ["sms_delivery_plugin"]
