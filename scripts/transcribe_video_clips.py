from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.knowledge import load_builtin_guidance  # noqa: E402
from video_storyboard.settings import model_override, require_api_key  # noqa: E402


def transcribe(path: Path, model: str, instruction: str) -> str:
    mime_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
    }.get(path.suffix.lower())
    if mime_type is None:
        raise ValueError(f"Unsupported transcription input: {path}")
    client = genai.Client(api_key=require_api_key())
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(
                data=path.read_bytes(),
                mime_type=mime_type,
            ),
            instruction,
        ],
    )
    return (response.text or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("clips", type=Path, nargs="+")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    guidance = load_builtin_guidance()
    model = args.model or model_override("asr") or guidance.profile.models.asr
    instruction = guidance.profile.audio.transcription_instruction
    for clip in args.clips:
        resolved = clip.resolve()
        print(f"{resolved.name}: {transcribe(resolved, model, instruction)}")


if __name__ == "__main__":
    main()
