from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import wave
from datetime import UTC, datetime
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()
TARGET_SPEECH_SECONDS = 2.68
MAX_TEMPO = 1.15


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
    ambience_profile: str,
) -> str:
    if ambience_profile == "space-to-nature":
        if shot_number <= 5:
            highpass, lowpass, volume = 40, 380, 0.016
        elif shot_number <= 7:
            highpass, lowpass, volume = 90, 1800, 0.030
        else:
            highpass, lowpass, volume = 70, 2300, 0.036
    else:
        highpass, lowpass, volume = 55, 700, 0.038
    return (
        f"[{input_index}:a]highpass=f={highpass},lowpass=f={lowpass},"
        f"volume={volume:.3f},"
        "afade=t=in:st=0:d=0.08,afade=t=out:st=2.82:d=0.18,"
        f"pan=stereo|c0=c0|c1=c0[amb{shot_number}]"
    )


def rebuild_clip(
    clip: Path,
    shot_number: int,
    speech: Path | None,
    chime: bool,
    ambience_profile: str,
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
        tempo = max(1.0, speech_duration / TARGET_SPEECH_SECONDS)
        if tempo > MAX_TEMPO:
            raise RuntimeError(
                f"S{shot_number:03d}: TTS {speech_duration:.3f}s needs "
                f"atempo={tempo:.3f}; regenerate shorter speech"
            )
        filters.append(
            f"[{next_input}:a]atempo={tempo:.8f},highpass=f=70,"
            "lowpass=f=11000,acompressor=threshold=-20dB:ratio=2.4:"
            "attack=8:release=100:makeup=2,volume=1.08,adelay=110:all=1,"
            "apad,atrim=duration=3,aresample=48000,"
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
            "3",
            "-i",
            (
                "anoisesrc=color=pink:amplitude=0.08:"
                f"sample_rate=48000:seed={6100 + shot_number}"
            ),
        ]
    )
    filters.append(ambience_filter(next_input, shot_number, ambience_profile))
    mix_labels.append(f"[amb{shot_number}]")
    next_input += 1

    if chime:
        args.extend(
            [
                "-f",
                "lavfi",
                "-t",
                "3",
                "-i",
                "sine=frequency=659.25:sample_rate=48000",
            ]
        )
        filters.append(
            f"[{next_input}:a]volume=0.030,atrim=duration=0.40,"
            "afade=t=in:st=0:d=0.02,afade=t=out:st=0.16:d=0.24,"
            "adelay=1180:all=1,apad,atrim=duration=3,"
            "pan=stereo|c0=c0|c1=c0[chime]"
        )
        mix_labels.append("[chime]")

    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0,"
        "alimiter=limit=0.92,atrim=duration=3[a]"
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
            "3",
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
        "ambience_profile": ambience_profile,
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
        "--ambience-profile",
        choices=["neutral", "space-to-nature"],
        default="neutral",
        help=(
            "Use neutral room tone or a deterministic progression from quiet "
            "space rumble to airy sky and broader natural ambience."
        ),
    )
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    storyboard = json.loads(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )
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
        report.append(
            rebuild_clip(
                clip,
                number,
                speech,
                number in set(args.chime_shot),
                args.ambience_profile,
            )
        )
        print(f"[clean soundtrack] S{number:03d}")

    destination = run_dir / "audio" / "clean_soundtrack.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "policy": "All video-generation API audio was removed.",
                "sample_rate_hz": 48000,
                "channels": 2,
                "ambience_profile": args.ambience_profile,
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
