from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.knowledge import (  # noqa: E402
    AmbienceInstructions,
    AudioInstructions,
    MediaContract,
    load_run_guidance,
)

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
        raise RuntimeError("\n".join(result.stderr.splitlines()[-50:]))


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def replace(destination: Path, temporary: Path) -> None:
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise RuntimeError(f"Temporary output missing: {temporary}")
    os.replace(temporary, destination)


def ambience_filter(
    input_index: int,
    shot_number: int,
    media: MediaContract,
    ambience_settings: dict[str, float] | None = None,
) -> str:
    settings = ambience_settings or {}
    highpass = int(settings.get("highpass_hz", 55))
    lowpass = int(settings.get("lowpass_hz", 700))
    volume = float(settings.get("volume", 0.038))
    fade_out_duration = min(0.18, media.shot_duration_seconds / 4)
    fade_out_start = media.shot_duration_seconds - fade_out_duration
    return (
        f"[{input_index}:a]highpass=f={highpass},lowpass=f={lowpass},"
        f"volume={volume:.3f},"
        f"afade=t=in:st=0:d=0.08,afade=t=out:st={fade_out_start:.2f}:"
        f"d={fade_out_duration:.2f},"
        f"pan=stereo|c0=c0|c1=c0[amb{shot_number}]"
    )


def rebuild_clip(
    clip: Path,
    shot_number: int,
    speech: Path | None,
    chime: bool,
    ambience_settings: dict[str, float],
    media: MediaContract,
    audio: AudioInstructions,
) -> dict[str, object]:
    temporary = clip.with_name(f"{clip.stem}.clean-audio.mp4")
    args = [
        "-i",
        str(clip),
    ]
    filters: list[str] = []
    mix_labels: list[str] = []
    next_input = 1

    if speech:
        args.extend(["-i", str(speech)])
        speech_duration = wav_duration(speech)
        tempo = max(1.0, speech_duration / audio.maximum_speech_seconds)
        if tempo > audio.maximum_tempo_factor:
            raise RuntimeError(
                f"S{shot_number:03d}: TTS {speech_duration:.3f}s needs "
                f"atempo={tempo:.3f}; regenerate shorter speech"
            )
        filters.append(
            f"[{next_input}:a]atempo={tempo:.8f},highpass=f=70,"
            "lowpass=f=11000,acompressor=threshold=-20dB:ratio=2.4:"
            "attack=8:release=100:makeup=2,volume=1.08,adelay=110:all=1,"
            f"apad,atrim=duration={media.shot_duration_seconds},aresample=48000,"
            "pan=stereo|c0=c0|c1=c0[speech]"
        )
        mix_labels.append("[speech]")
        next_input += 1
    else:
        speech_duration = None
        tempo = None

    args.extend(
        [
            "-f",
            "lavfi",
            "-t",
            str(media.shot_duration_seconds),
            "-i",
            (
                "anoisesrc=color=pink:amplitude=0.08:"
                f"sample_rate=48000:seed={6100 + shot_number}"
            ),
        ]
    )
    filters.append(
        ambience_filter(next_input, shot_number, media, ambience_settings)
    )
    mix_labels.append(f"[amb{shot_number}]")
    next_input += 1

    if chime:
        args.extend(
            [
                "-f",
                "lavfi",
                "-t",
                str(media.shot_duration_seconds),
                "-i",
                "sine=frequency=659.25:sample_rate=48000",
            ]
        )
        filters.append(
            f"[{next_input}:a]volume=0.030,atrim=duration=0.40,"
            "afade=t=in:st=0:d=0.02,afade=t=out:st=0.16:d=0.24,"
            f"adelay=1180:all=1,apad,atrim=duration={media.shot_duration_seconds},"
            "pan=stereo|c0=c0|c1=c0[chime]"
        )
        mix_labels.append("[chime]")

    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0,"
        f"alimiter=limit=0.92,atrim=duration={media.shot_duration_seconds}[a]"
    )
    args.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-t",
            str(media.shot_duration_seconds),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(temporary),
        ]
    )
    run_ffmpeg(args)
    replace(clip, temporary)
    return {
        "shot_number": shot_number,
        "audio_source": (
            "dedicated_tts_and_local_ambience"
            if speech
            else "local_non_tonal_ambience"
        ),
        "tts_duration_seconds": (
            round(speech_duration, 3) if speech_duration is not None else None
        ),
        "tempo_factor": round(tempo, 6) if tempo is not None else None,
        "local_success_chime": chime,
        "ambience_settings": ambience_settings,
        "video_api_audio_used": False,
        "third_party_music_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove video-API audio and build a deterministic local mix."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--chime-shot", type=int, action="append", default=[])
    parser.add_argument(
        "--ambience-config",
        type=Path,
        help=(
            "Optional work-specific JSON with default and per-shot ambience settings."
        ),
    )
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    guidance = load_run_guidance(run_dir)
    media = guidance.profile.media
    audio = guidance.profile.audio
    storyboard = json.loads(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )
    ambience_config = {
        "default": audio.default_ambience.model_dump(),
        "shots": {},
    }
    if args.ambience_config:
        ambience_config = json.loads(
            args.ambience_config.resolve().read_text(encoding="utf-8")
        )
        if not isinstance(ambience_config.get("default"), dict) or not isinstance(
            ambience_config.get("shots", {}), dict
        ):
            raise ValueError("ambience config requires object fields: default and shots")
    clips_dir = run_dir / "video" / "clips"
    backup = run_dir / "rejected" / "before_clean_soundtrack" / "video" / "clips"
    backup.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, object]] = []

    for shot in storyboard["shots"]:
        number = int(shot["shot_number"])
        clip = clips_dir / f"shot_{number:03d}.mp4"
        if not clip.is_file():
            raise FileNotFoundError(clip)
        backup_clip = backup / clip.name
        if not backup_clip.exists():
            shutil.copy2(clip, backup_clip)
        speech = run_dir / "audio" / "tts" / f"shot_{number:03d}.wav"
        if not shot.get("dialogue"):
            speech = None
        elif not speech.is_file():
            raise FileNotFoundError(speech)
        ambience_settings = AmbienceInstructions.model_validate(
            {
                **ambience_config["default"],
                **ambience_config.get("shots", {}).get(str(number), {}),
            }
        ).model_dump()
        report.append(
            rebuild_clip(
                clip,
                number,
                speech,
                number in set(args.chime_shot),
                ambience_settings,
                media,
                audio,
            )
        )
        print(f"[clean soundtrack] S{number:03d}")

    destination = run_dir / "audio" / "clean_soundtrack.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "knowledge_version": guidance.manifest.knowledge_version,
                "policy": "All video-generation API audio was removed.",
                "sample_rate_hz": 48000,
                "channels": 2,
                "ambience_config": (
                    str(args.ambience_config.resolve())
                    if args.ambience_config
                    else None
                ),
                "third_party_music_used": False,
                "shots": report,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(destination)


if __name__ == "__main__":
    main()
