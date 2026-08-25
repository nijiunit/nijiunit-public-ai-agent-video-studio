from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_CONFIG_PATH = ROOT / "config" / "runtime.json"


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["1.0"] = "1.0"
    tutorial_base_url: str
    github_repository_url: str
    request_timeout_seconds: int = Field(default=20, ge=1, le=60)
    maximum_page_bytes: int = Field(default=2_097_152, ge=1_024, le=10_485_760)


def load_runtime_config(
    path: Path = DEFAULT_RUNTIME_CONFIG_PATH,
) -> RuntimeConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    tutorial_override = os.getenv("NIJIUNIT_TUTORIAL_BASE_URL", "").strip()
    if tutorial_override:
        raw["tutorial_base_url"] = tutorial_override
    return RuntimeConfig.model_validate(raw)
