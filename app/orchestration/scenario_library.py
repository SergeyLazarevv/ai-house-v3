from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


@dataclass(frozen=True)
class LoadedScenario:
    scenario_id: str
    body_markdown: str
    synthesis_system: str | None
    required_slots: tuple[str, ...]


_LIBRARY: dict[str, LoadedScenario] | None = None


def _parse_markdown_file(path: Path) -> LoadedScenario | None:
    raw = path.read_text(encoding="utf-8")
    scenario_id: str | None = None
    synthesis_system: str | None = None
    required_slots: tuple[str, ...] = ()
    body = raw.strip()

    if raw.lstrip().startswith("+++"):
        parts = raw.split("+++", 2)
        if len(parts) >= 3:
            meta_block = parts[1].strip()
            body = parts[2].lstrip("\n").strip()
            try:
                meta: dict[str, Any] = tomllib.loads(meta_block)
            except tomllib.TOMLDecodeError as exc:
                logger.warning("Сценарий %s: ошибка TOML frontmatter: %s", path.name, exc)
                meta = {}
            if isinstance(meta, dict):
                sid = meta.get("scenario_id")
                if isinstance(sid, str) and sid.strip():
                    scenario_id = sid.strip()
                ss = meta.get("synthesis_system")
                if isinstance(ss, str) and ss.strip():
                    synthesis_system = ss.strip()
                rs = meta.get("required_slots")
                if isinstance(rs, list):
                    required_slots = tuple(str(x).strip() for x in rs if str(x).strip())

    if not scenario_id:
        scenario_id = path.stem.strip()
    if not scenario_id:
        return None

    return LoadedScenario(
        scenario_id=scenario_id,
        body_markdown=body,
        synthesis_system=synthesis_system,
        required_slots=required_slots,
    )


def load_scenario_library(*, force_reload: bool = False) -> dict[str, LoadedScenario]:
    global _LIBRARY
    if _LIBRARY is not None and not force_reload:
        return _LIBRARY
    out: dict[str, LoadedScenario] = {}
    if not SCENARIOS_DIR.is_dir():
        _LIBRARY = out
        return _LIBRARY
    for path in sorted(SCENARIOS_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        loaded = _parse_markdown_file(path)
        if loaded is None:
            continue
        if loaded.scenario_id in out:
            logger.warning("Дубликат scenario_id=%s в %s", loaded.scenario_id, path)
        out[loaded.scenario_id] = loaded
        logger.info("Загружен сценарий markdown: %s из %s", loaded.scenario_id, path.name)
    _LIBRARY = out
    return _LIBRARY


def get_loaded_scenario(scenario_id: str) -> LoadedScenario | None:
    return load_scenario_library().get((scenario_id or "").strip())


def get_synthesis_system_prompt(scenario_id: str) -> str | None:
    sc = get_loaded_scenario(scenario_id)
    if not sc:
        return None
    return sc.synthesis_system


def build_supervisor_scenarios_text() -> str:
    parts: list[str] = []
    for sid in sorted(load_scenario_library().keys()):
        sc = load_scenario_library()[sid]
        parts.append(f"### {sid}\n{sc.body_markdown.strip()}")
    return "\n\n".join(parts).strip()
