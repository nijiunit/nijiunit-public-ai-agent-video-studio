from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.character_registry import CharacterRegistry  # noqa: E402
from video_storyboard.video import inspect_video  # noqa: E402


def maximum_frame_delta(frames: list[Path]) -> float:
    with Image.open(frames[0]) as image:
        base = image.convert("RGB")
    values: list[float] = []
    for frame in frames[1:]:
        with Image.open(frame) as image:
            difference = ImageChops.difference(base, image.convert("RGB"))
        values.append(sum(ImageStat.Stat(difference).mean) / 3)
    return max(values, default=0.0)


def validate(registry_dir: Path) -> list[str]:
    registry = CharacterRegistry.load(registry_dir)
    issues = registry.validate()
    clip_count = 0
    for record in registry.records:
        motions = []
        if record.design_video:
            motions.append(record.design_video)
        motions.extend(record.motions)
        start_frame = (
            registry.asset_path(record, motions[0].clip_path).parent
            / "start_frame.png"
            if motions
            else None
        )
        if start_frame is None or not start_frame.is_file():
            issues.append(f"Missing design start frame: {record.id}")
        else:
            with Image.open(start_frame) as image:
                ratio = image.width / image.height
            if abs(ratio - 16 / 9) > 0.01:
                issues.append(
                    f"Start frame is not 16:9: {record.id}: {ratio:.4f}"
                )

        for motion in motions:
            clip_count += 1
            if "/design_videos/" not in f"/{motion.clip_path.replace(chr(92), '/')}" :
                issues.append(
                    f"Active clip is outside design_videos: {record.id}/{motion.id}: "
                    f"{motion.clip_path}"
                )
                continue
            clip = registry.asset_path(record, motion.clip_path)
            info = inspect_video(clip)
            if abs((info["duration_seconds"] or 0) - 3.0) > 0.05:
                issues.append(f"Wrong duration: {record.id}/{motion.id}: {info}")
            if (info["width"], info["height"]) != (1280, 720):
                issues.append(f"Wrong dimensions: {record.id}/{motion.id}: {info}")
            if abs((info["fps"] or 0) - 24.0) > 0.1:
                issues.append(f"Wrong frame rate: {record.id}/{motion.id}: {info}")
            frame_dir = clip.parent / f"{motion.id}_frames"
            frames = sorted(frame_dir.glob("frame_*.jpg"))
            if len(frames) != 9:
                issues.append(
                    f"Expected 9 review frames: {record.id}/{motion.id}: "
                    f"found {len(frames)}"
                )
            elif maximum_frame_delta(frames) <= 0.8:
                issues.append(
                    f"Motion appears static: {record.id}/{motion.id}"
                )
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=ROOT / "characters",
    )
    args = parser.parse_args()
    issues = validate(args.registry_dir.resolve())
    if issues:
        raise SystemExit("\n".join(issues))
    print(
        "character_design_videos=PASS: all clips are 3.00s, 1280x720, "
        "24fps, have 9 review frames, and contain visible motion"
    )


if __name__ == "__main__":
    main()
