from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.knowledge import (  # noqa: E402
    MediaContract,
    SubtitleInstructions,
    load_run_guidance,
)
from video_storyboard.video import extract_nine_frames  # noqa: E402

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
        raise RuntimeError("\n".join(result.stderr.splitlines()[-60:]))


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def ass_document(
    line: str,
    media: MediaContract,
    subtitle: SubtitleInstructions,
) -> str:
    end_time = media.shot_duration_seconds - subtitle.end_padding_seconds
    if end_time <= subtitle.start_seconds:
        raise ValueError("subtitle display interval must be positive")
    bold = -1 if subtitle.bold else 0
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {media.width}
PlayResY: {media.height}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Dialogue,{subtitle.font_name},{subtitle.font_size},{subtitle.primary_colour},{subtitle.primary_colour},{subtitle.outline_colour},{subtitle.back_colour},{bold},0,0,0,100,100,0,0,{subtitle.border_style},{subtitle.outline},{subtitle.shadow},{subtitle.alignment},{subtitle.margin_horizontal},{subtitle.margin_horizontal},{subtitle.margin_vertical},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:{subtitle.start_seconds:05.2f},0:00:{end_time:05.2f},Dialogue,,0,0,0,,{{\fad({subtitle.fade_in_milliseconds},{subtitle.fade_out_milliseconds})}}{ass_escape(line)}
"""


def filter_path(path: Path, root: Path) -> str:
    value = path.relative_to(root).as_posix()
    return value.replace(":", r"\:").replace("'", r"\'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render exact storyboard dialogue as local ASS subtitles."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    guidance = load_run_guidance(run_dir)
    media = guidance.profile.media
    subtitle_profile = guidance.profile.audio.subtitle
    storyboard = json.loads(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )
    overlay_dir = run_dir / "overlays"
    backup_dir = run_dir / "rejected" / "before_local_subtitles" / "video" / "clips"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    for shot in storyboard["shots"]:
        line = str(shot.get("dialogue") or "").strip()
        if not line:
            continue
        number = int(shot["shot_number"])
        clip = run_dir / "video" / "clips" / f"shot_{number:03d}.mp4"
        subtitle = overlay_dir / f"shot_{number:03d}.ass"
        subtitle.write_text(
            ass_document(line, media, subtitle_profile),
            encoding="utf-8",
        )
        backup = backup_dir / clip.name
        if not backup.exists():
            shutil.copy2(clip, backup)
        temporary = clip.with_name(f"{clip.stem}.subtitled.mp4")
        run_ffmpeg(
            [
                "-i",
                str(clip),
                "-vf",
                f"ass='{filter_path(subtitle, ROOT)}'",
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-t",
                str(media.shot_duration_seconds),
                "-r",
                str(media.frames_per_second),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(temporary),
            ]
        )
        os.replace(temporary, clip)
        extract_nine_frames(
            clip,
            run_dir / "frames" / f"shot_{number:03d}",
            media,
        )
        print(f"[subtitle] S{number:03d}: {line}")


if __name__ == "__main__":
    main()
