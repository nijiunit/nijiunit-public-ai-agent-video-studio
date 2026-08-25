from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.character_registry import (  # noqa: E402
    CharacterMotion,
    CharacterRecord,
    CharacterRegistry,
)
from video_storyboard.knowledge import (  # noqa: E402
    MediaContract,
    ProductionProfile,
    ensure_production_allowed,
    load_builtin_guidance,
)
from video_storyboard.schema import Shot  # noqa: E402
from video_storyboard.video import (  # noqa: E402
    VideoService,
    extract_nine_frames,
    inspect_video,
    standardize_clip,
)

DESIGN_MEDIA = MediaContract(
    shot_duration_seconds=3,
    aspect_ratio="16:9",
    width=1280,
    height=720,
    frames_per_second=24,
    review_frames_per_second=3,
)


def remove_audio_track(path: Path) -> None:
    temporary = path.with_name(f"{path.stem}.silent.mp4")
    result = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-y",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-an",
            "-movflags",
            "+faststart",
            str(temporary),
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("\n".join(result.stderr.splitlines()[-40:]))
    os.replace(temporary, path)


def make_shot(record: CharacterRecord, motion: CharacterMotion) -> Shot:
    return Shot(
        shot_number=1,
        title=f"{record.name_ja}: {motion.name_ja}",
        story_purpose="authoritative character-design motion reference",
        scene_description=(
            "The exact single character remains alone on the neutral studio "
            "background from the supplied first frame."
        ),
        characters=[record.name_ja],
        action=motion.name_ja,
        emotion="stable characteristic presence",
        camera="absolutely locked camera; no pan, tilt, zoom, dolly, crop, or cut",
        lighting="preserve the exact soft studio lighting from the first frame",
        sound="silent neutral room tone only",
        continuity=(
            "preserve exact identity, anatomy, scale, materials, colors, "
            "background, framing, and 16:9 proportions throughout"
        ),
        reference_assets=[],
        main_image_prompt="not used",
        video_prompt=motion.prompt_en,
        frame_descriptions=[motion.name_ja for _ in range(9)],
    )


def render_motion(
    service: VideoService,
    profile: ProductionProfile,
    registry: CharacterRegistry,
    record: CharacterRecord,
    motion: CharacterMotion,
    overwrite: bool,
    keep_provider_artifacts: bool,
) -> Path:
    clip = registry.asset_path(record, motion.clip_path)
    directory = clip.parent
    start_frame = directory / "start_frame.png"
    raw = directory / f"{motion.id}_raw.mp4"
    metadata = directory / f"{motion.id}_metadata.json"
    frames = directory / f"{motion.id}_frames"
    if not start_frame.is_file():
        raise FileNotFoundError(start_frame)
    if clip.is_file() and not overwrite:
        print(f"[skip] {record.id}/{motion.id}", flush=True)
        return clip

    directory.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        try:
            print(f"[generate {attempt}/3] {record.id}/{motion.id}", flush=True)
            service.create_clip(
                make_shot(record, motion),
                start_frame,
                raw,
                metadata,
                character_lock=None,
            )
            standardize_clip(raw, clip, profile.media)
            remove_audio_track(clip)
            extract_nine_frames(clip, frames, profile.media)
            design_metadata = {
                "schema_version": "1.0",
                "status": "candidate",
                "source_policy": "new_generation_from_publishable_identity_only",
                "character_id": record.id,
                "character_name": record.name_ja,
                "profile_version": record.version,
                "motion_id": motion.id,
                "action_ja": motion.name_ja,
                "start_frame": start_frame.name,
                "clip": clip.name,
                "prompt_en": motion.prompt_en,
                "knowledge_version": profile.knowledge_version,
                "media_contract": profile.media.model_dump(),
                "inspection": inspect_video(clip),
            }
            (directory / f"{motion.id}_design.json").write_text(
                json.dumps(design_metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if not keep_provider_artifacts:
                raw.unlink(missing_ok=True)
                metadata.unlink(missing_ok=True)
            return clip
        except Exception as exc:
            if attempt == 3:
                raise
            print(f"[retry] {record.id}/{motion.id}: {exc}", flush=True)
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate design-presence and action clips declared by a registry."
    )
    parser.add_argument("--registry-dir", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--keep-provider-artifacts",
        action="store_true",
        help="Keep raw provider video and response metadata for local debugging.",
    )
    args = parser.parse_args()

    registry = CharacterRegistry.load(args.registry_dir.resolve())
    selected: list[tuple[CharacterRecord, CharacterMotion]] = []
    for record in registry.records:
        motions = ([record.design_video] if record.design_video else []) + record.motions
        for motion in motions:
            if (
                not args.only
                or record.id in args.only
                or motion.id in args.only
                or f"{record.id}/{motion.id}" in args.only
            ):
                selected.append((record, motion))
    if not selected:
        raise SystemExit("No matching character or motion id.")

    guidance = load_builtin_guidance()
    ensure_production_allowed(guidance, "ja")
    design_profile = guidance.profile.model_copy(update={"media": DESIGN_MEDIA})
    service = VideoService(profile=design_profile, model=args.model)
    for record, motion in selected:
        print(
            f"[done] {render_motion(service, design_profile, registry, record, motion, args.overwrite, args.keep_provider_artifacts)}",
            flush=True,
        )


if __name__ == "__main__":
    main()
