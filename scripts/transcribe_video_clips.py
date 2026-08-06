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

from video_storyboard.settings import require_api_key  # noqa: E402


def transcribe(path: Path, model: str) -> str:
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
            (
                "この短い動画の音声を一字一句そのまま日本語で文字起こししてください。"
                "説明、要約、補足、引用符は不要です。聞こえない箇所は［不明］と記載してください。"
            ),
        ],
    )
    return (response.text or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("clips", type=Path, nargs="+")
    parser.add_argument("--model", default="gemini-3-flash-preview")
    args = parser.parse_args()
    for clip in args.clips:
        resolved = clip.resolve()
        print(f"{resolved.name}: {transcribe(resolved, args.model)}")


if __name__ == "__main__":
    main()
