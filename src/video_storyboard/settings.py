from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def require_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"GEMINI_API_KEYが未設定です。{ROOT / '.env'}へ入力してください。"
        )
    return api_key



def model_override(role: str) -> str | None:
    """Return an explicit local override; defaults come from remote guidance."""
    value = os.getenv(f"{role.upper()}_MODEL", "").strip()
    return value or None


CHARACTER_REGISTRY_DIR = Path(
    os.getenv("CHARACTER_REGISTRY_DIR", str(ROOT / "characters"))
).resolve()
