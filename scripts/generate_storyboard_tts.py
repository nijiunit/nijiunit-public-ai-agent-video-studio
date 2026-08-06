from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

from google import genai
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.settings import TTS_MODEL, require_api_key  # noqa: E402

DEFAULT_MODEL = TTS_MODEL
FFMPEG = get_ffmpeg_exe()


def run_ffmpeg(arguments: list[str]) -> None:
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-y", *arguments],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("\n".join(result.stderr.splitlines()[-40:]))


def save_audio(audio: object, destination: Path) -> None:
    audio_bytes = base64.b64decode(audio.data)
    if audio.mime_type == "audio/wav":
        destination.write_bytes(audio_bytes)
        return
    with wave.open(str(destination), "wb") as wav_file:
        wav_file.setnchannels(audio.channels or 1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(audio.sample_rate or 24000)
        wav_file.writeframes(audio_bytes)


def standardize(source: Path, destination: Path) -> None:
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-af",
            (
                "silenceremove=start_periods=1:start_duration=0.02:"
                "start_threshold=-50dB,areverse,"
                "silenceremove=start_periods=1:start_duration=0.02:"
                "start_threshold=-50dB,areverse"
            ),
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def create_audio(
    client: genai.Client,
    model: str,
    voice: str,
    prompt: str,
    shot_number: int,
) -> object:
    for attempt in range(1, 4):
        try:
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice}]},
                background=False,
                store=False,
            )
            audio = interaction.output_audio
            if audio is None or not audio.data:
                raise RuntimeError(f"S{shot_number:03d}: no TTS audio returned")
            return audio
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3 * attempt)
    raise AssertionError("unreachable")


def load_voice_overrides(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    config = json.loads(path.resolve().read_text(encoding="utf-8"))
    shots = config.get("shots", {})
    if not isinstance(shots, dict):
        raise ValueError("voice config 'shots' must be an object")
    overrides: dict[str, dict[str, str]] = {}
    for key, value in shots.items():
        if not isinstance(value, dict):
            raise ValueError(f"voice config shot {key!r} must be an object")
        overrides[str(key)] = {
            str(field): str(setting) for field, setting in value.items()
        }
    return overrides


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate dedicated TTS for every storyboard dialogue line."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--voice", default="Achird")
    parser.add_argument("--speaker", default="calm friendly character")
    parser.add_argument(
        "--voice-config",
        type=Path,
        help=(
            "Optional UTF-8 JSON file with a 'shots' object. Each shot number "
            "may override voice, speaker, and style."
        ),
    )
    parser.add_argument(
        "--style",
        default=(
            "Warm, compact, friendly Japanese delivery. Speak clearly and "
            "naturally, with short pauses, finishing within 2.55 seconds."
        ),
    )
    args = parser.parse_args()

    voice_overrides = load_voice_overrides(args.voice_config)

    run_dir = args.run_dir.resolve()
    storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
    lines = [shot for shot in storyboard["shots"] if shot.get("dialogue")]
    raw_dir = run_dir / "audio" / "tts_raw"
    output_dir = run_dir / "audio" / "tts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=require_api_key())

    report: list[dict[str, object]] = []
    for shot in lines:
        number = int(shot["shot_number"])
        line = str(shot["dialogue"])
        override = voice_overrides.get(str(number), {})
        voice = str(override.get("voice", args.voice))
        speaker = str(override.get("speaker", args.speaker))
        style = str(override.get("style", args.style))
        raw = raw_dir / f"shot_{number:03d}.wav"
        destination = output_dir / f"shot_{number:03d}.wav"
        prompt = (
            "Read only the following Japanese sentence. Do not add a speaker "
            "name, explanation, paraphrase, repetition, laugh, or sigh. "
            f"Speaker: {speaker}. Style: {style}\nSentence: {line}"
        )
        if not destination.exists():
            audio = create_audio(client, args.model, voice, prompt, number)
            save_audio(audio, raw)
            standardize(raw, destination)
        item = {
            "shot_number": number,
            "speaker": speaker,
            "voice": voice,
            "line": line,
            "duration_seconds": round(duration(destination), 3),
        }
        report.append(item)
        print(f"[tts] S{number:03d} {item['duration_seconds']:.3f}s")

    (run_dir / "audio" / "tts_report.json").write_text(
        json.dumps(
            {
                "model": args.model,
                "video_api_audio_used": False,
                "shots": report,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
