from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe local audio files with faster-whisper."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--model", default="small")
    parser.add_argument("--vad-filter", action="store_true")
    args = parser.parse_args()

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    for path in args.paths:
        segments, info = model.transcribe(
            str(path),
            language="ja",
            beam_size=5,
            vad_filter=args.vad_filter,
        )
        print(f"[{path.name}] language={info.language}")
        for segment in segments:
            print(f"{segment.start:5.2f}-{segment.end:5.2f} {segment.text.strip()}")


if __name__ == "__main__":
    main()
