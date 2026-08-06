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


STORY_MODEL = os.getenv("STORY_MODEL", "gemini-3.6-flash")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3.1-flash-image")
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "gemini-omni-flash-preview")
TTS_MODEL = os.getenv("TTS_MODEL", "gemini-3.1-flash-tts-preview")
CHARACTER_REGISTRY_DIR = Path(
    os.getenv("CHARACTER_REGISTRY_DIR", str(ROOT / "characters"))
).resolve()
MAX_CHARACTER_REFERENCE_IMAGES = int(os.getenv("MAX_CHARACTER_REFERENCE_IMAGES", "6"))
