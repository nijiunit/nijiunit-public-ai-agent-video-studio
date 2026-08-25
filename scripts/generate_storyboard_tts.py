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

from video_storyboard.knowledge import (  # noqa: E402
    ensure_production_allowed,
    load_builtin_guidance,
    load_run_guidance,
)
from video_storyboard.settings import model_override, require_api_key  # noqa: E402

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
    parser.add_argument("--model", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--speaker", default=None)
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
        default=None,
    )
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    ensure_production_allowed(load_builtin_guidance(), "ja")
    guidance = load_run_guidance(run_dir)
    audio_profile = guidance.profile.audio
    model = args.model or model_override("tts") or guidance.profile.models.tts
    default_voice = args.voice or audio_profile.default_voice
    default_speaker = args.speaker or audio_profile.default_speaker
    default_style = args.style or audio_profile.default_style
    voice_overrides = load_voice_overrides(args.voice_config)
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
        voice = str(override.get("voice", default_voice))
        speaker = str(override.get("speaker", default_speaker))
        style = str(override.get("style", default_style))
        raw = raw_dir / f"shot_{number:03d}.wav"
        destination = output_dir / f"shot_{number:03d}.wav"
        prompt = (
            "Read only the following sentence. Do not add a speaker "
            "name, explanation, paraphrase, repetition, laugh, or sigh. "
            f"Language: {audio_profile.tts_language_instruction}. "
            f"Finish within {audio_profile.maximum_speech_seconds:.2f} seconds. "
            f"Speaker: {speaker}. Style: {style}\nSentence: {line}"
        )
        if not destination.exists():
            audio = create_audio(client, model, voice, prompt, number)
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
                "model": model,
                "knowledge_version": guidance.manifest.knowledge_version,
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
