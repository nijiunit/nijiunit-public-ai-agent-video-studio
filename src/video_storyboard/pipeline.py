from __future__ import annotations

import json
import re
from pathlib import Path

from .assets import (
    load_manifest,
    prepare_assets,
    read_story,
    save_manifest,
)
from .character_registry import CharacterRegistry
from .gemini_service import GeminiService
from .motion_assets import prepare_motion_keyframes
from .schema import Storyboard
from .settings import CHARACTER_REGISTRY_DIR
from .video import concatenate_clips, inspect_video, render_video_shots
from .workbook import (
    create_video_workbook,
    create_workbook,
    extract_corrections,
)


def _next_run_dir(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    versions: list[int] = []
    for path in output_root.iterdir():
        match = re.fullmatch(r"v(\d{3})", path.name)
        if path.is_dir() and match:
            versions.append(int(match.group(1)))
    version = max(versions, default=0) + 1
    run_dir = output_root / f"v{version:03d}"
    run_dir.mkdir()
    return run_dir


def _load_storyboard(run_dir: Path) -> Storyboard:
    return Storyboard.model_validate_json(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )


def create_command(
    input_dir: Path,
    output_root: Path,
    story_model: str | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    input_dir = input_dir.resolve()
    run_dir = _next_run_dir(output_root.resolve())
    reference_dir = run_dir / "references"
    reference_dir.mkdir()

    print(f"[1/3] ストーリーを読み込み: {input_dir}")
    story_path, story = read_story(input_dir)
    print("[2/3] 参照素材を準備")
    assets = prepare_assets(input_dir, reference_dir)
    save_manifest(assets, story_path, run_dir / "manifest.json")

    print("[3/3] Geminiで3秒構成を生成")
    service = GeminiService(story_model=story_model)
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    storyboard = service.create_storyboard(
        story,
        assets,
        input_dir,
        character_registry,
    )
    (run_dir / "storyboard.json").write_text(
        storyboard.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(
        f"構成完了: {len(storyboard.shots)}シート / "
        f"{storyboard.total_duration_seconds}秒"
    )
    return str(run_dir)


def create_storyboard_in_run_command(
    input_dir: Path,
    run_dir: Path,
    story_model: str | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    """Resume storyboard generation after references were already prepared."""
    input_dir = input_dir.resolve()
    run_dir = run_dir.resolve()
    _, story = read_story(input_dir)
    assets = load_manifest(run_dir / "manifest.json")
    service = GeminiService(story_model=story_model)
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    storyboard = service.create_storyboard(
        story,
        assets,
        input_dir,
        character_registry,
    )
    (run_dir / "storyboard.json").write_text(
        storyboard.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return str(run_dir)


def render_images_command(
    run_dir: Path,
    image_model: str | None = None,
    limit: int | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    assets = load_manifest(run_dir / "manifest.json")
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    if character_registry:
        issues = character_registry.validate()
        if issues:
            raise RuntimeError(
                "Invalid character registry:\n" + "\n".join(issues)
            )
    service = GeminiService(image_model=image_model)
    generated = 0
    for index, shot in enumerate(storyboard.shots):
        destination = run_dir / "images" / f"shot_{shot.shot_number:03d}.png"
        if destination.exists():
            print(f"[skip] S{shot.shot_number:03d}: 生成済み")
            continue
        if limit is not None and generated >= limit:
            break
        print(
            f"[{generated + 1}] S{shot.shot_number:03d}: "
            f"{shot.title} のメイン画像を生成"
        )
        service.create_main_image(
            storyboard,
            index,
            assets,
            destination,
            character_registry,
        )
        generated += 1
    missing = sum(
        not (run_dir / "images" / f"shot_{shot.shot_number:03d}.png").exists()
        for shot in storyboard.shots
    )
    return f"生成={generated}枚、残り={missing}枚: {run_dir / 'images'}"


def build_workbook_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    assets = load_manifest(run_dir / "manifest.json")
    destination = run_dir / f"storyboard_{run_dir.name}.xlsx"
    create_workbook(storyboard, run_dir, assets, destination)
    return str(destination)


def render_videos_command(
    run_dir: Path,
    video_model: str | None = None,
    limit: int | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    completed = render_video_shots(
        storyboard=storyboard,
        run_dir=run_dir,
        model=video_model,
        limit=limit,
        character_registry_dir=character_registry_dir,
    )
    return f"completed={len(completed)}: {run_dir / 'video' / 'clips'}"


def validate_character_registry_command(registry_dir: Path) -> str:
    registry = CharacterRegistry.load(registry_dir.resolve())
    issues = registry.validate()
    if issues:
        raise RuntimeError(
            "Invalid character registry:\n" + "\n".join(issues)
        )
    lock_path = registry.write_lock_file()
    names = ", ".join(
        f"{record.name_ja}/{record.version}" for record in registry.records
    )
    return f"characters={len(registry.records)}: {names}; lock={lock_path}"


def prepare_motion_keyframes_command(
    registry_dir: Path,
    overwrite: bool = False,
) -> str:
    generated = prepare_motion_keyframes(registry_dir.resolve(), overwrite)
    return f"motion_keyframes_generated={len(generated)}: {registry_dir.resolve()}"


def finalize_video_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    destination = run_dir / "final" / f"story_video_{run_dir.name}.mp4"
    concatenate_clips(storyboard, run_dir, destination)
    metadata = inspect_video(destination)
    (destination.parent / "video_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(destination)


def build_video_workbook_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    source = run_dir / f"storyboard_{run_dir.name}.xlsx"
    if not source.exists():
        assets = load_manifest(run_dir / "manifest.json")
        create_workbook(storyboard, run_dir, assets, source)
    destination = run_dir / "final" / f"storyboard_{run_dir.name}_video.xlsx"
    create_video_workbook(storyboard, source, run_dir, destination)
    return str(destination)


def extract_corrections_command(
    workbook_path: Path,
    output_path: Path | None = None,
) -> str:
    workbook_path = workbook_path.resolve()
    destination = (
        output_path.resolve()
        if output_path
        else workbook_path.parent / "corrections.json"
    )
    extract_corrections(workbook_path, destination)
    return str(destination)
