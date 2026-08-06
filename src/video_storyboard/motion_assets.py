from __future__ import annotations

import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .character_registry import CharacterRegistry


def _extract_frame(source: Path, seconds: float, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(destination),
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode or not destination.is_file():
        raise RuntimeError(
            f"Could not extract {seconds:.3f}s from {source}:\n{result.stderr}"
        )


def prepare_motion_keyframes(
    registry_dir: Path,
    overwrite: bool = False,
) -> list[Path]:
    registry = CharacterRegistry.load(registry_dir)
    generated: list[Path] = []
    for record in registry.records:
        motions = list(record.motions)
        if record.design_video:
            motions.insert(0, record.design_video)
        for motion in motions:
            clip = registry.asset_path(record, motion.clip_path)
            if not clip.is_file():
                raise FileNotFoundError(
                    f"Missing motion clip: {record.id}/{motion.id}: {clip}"
                )
            for relative_path, seconds in zip(
                motion.keyframes,
                motion.keyframe_times_seconds,
                strict=True,
            ):
                destination = registry.asset_path(record, relative_path)
                if destination.is_file() and not overwrite:
                    continue
                _extract_frame(clip, seconds, destination)
                generated.append(destination)
    return generated
