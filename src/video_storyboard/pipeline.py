from __future__ import annotations

import json
import re
from pathlib import Path

from .artifacts import (
    artifact_for_reveal,
    current_storyboard_workbook,
    next_storyboard_workbook,
    next_video_review_workbook,
    reveal_in_file_manager,
    review_html_path,
)
from .assets import (
    load_manifest,
    prepare_assets,
    read_story,
    save_manifest,
)
from .character_registry import CharacterRegistry
from .gemini_service import GeminiService
from .motion_assets import prepare_motion_keyframes
from .review_html import create_review_html
from .schema import Storyboard
from .settings import CHARACTER_REGISTRY_DIR
from .video import concatenate_clips, inspect_video, render_video_shots
from .workbook import (
    approve_workbook,
    create_video_workbook,
    create_workbook,
    extract_corrections,
    workbook_review_issues,
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


def _workbook_path(run_dir: Path) -> Path:
    return current_storyboard_workbook(run_dir)


def _build_storyboard_review_bundle(
    storyboard: Storyboard,
    run_dir: Path,
    assets,
    destination: Path,
) -> tuple[Path, Path, Path]:
    create_workbook(storyboard, run_dir, assets, destination)
    japanese_html = create_review_html(
        storyboard,
        run_dir,
        review_html_path(destination, "ja"),
        language="ja",
    )
    english_html = create_review_html(
        storyboard,
        run_dir,
        review_html_path(destination, "en"),
        language="en",
    )
    return destination, japanese_html, english_html


def _missing_storyboard_images(
    storyboard: Storyboard,
    run_dir: Path,
) -> list[str]:
    return [
        f"shot_{shot.shot_number:03d}.png"
        for shot in storyboard.shots
        if not (
            run_dir / "images" / f"shot_{shot.shot_number:03d}.png"
        ).exists()
    ]


def _require_storyboard_images(
    storyboard: Storyboard,
    run_dir: Path,
) -> None:
    missing = _missing_storyboard_images(storyboard, run_dir)
    if missing:
        raise RuntimeError(
            "Excelコンテには全ショットのメイン画像が必要です。"
            "先に render-images を完了してください。\n"
            "Missing storyboard images: " + ", ".join(missing)
        )


def _require_approved_workbook(
    storyboard: Storyboard,
    run_dir: Path,
) -> Path:
    workbook_path = _workbook_path(run_dir)
    issues = workbook_review_issues(storyboard, workbook_path)
    if issues:
        raise RuntimeError(
            "Excelコンテの確認と承認が終わるまで動画は生成できません。\n"
            "Review and approve the Excel storyboard before video generation.\n"
            + "\n".join(issues)
            + "\nExcelを確認後、利用者が承認した場合だけ "
            "approve-workbook を実行してください。"
        )
    return workbook_path


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
    print(
        "次はメイン画像を生成し、Excelコンテを作成します。"
        "Excelの利用者承認前に動画生成へ進まないでください。"
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
    missing = _missing_storyboard_images(storyboard, run_dir)
    workbook_note = ""
    if not missing:
        workbook_path = _workbook_path(run_dir)
        if not workbook_path.exists():
            workbook_path = next_storyboard_workbook(run_dir)
            _build_storyboard_review_bundle(
                storyboard,
                run_dir,
                assets,
                workbook_path,
            )
        else:
            for language in ("ja", "en"):
                html_path = review_html_path(workbook_path, language)
                if not html_path.is_file():
                    create_review_html(
                        storyboard,
                        run_dir,
                        html_path,
                        language=language,
                    )
        workbook_note = (
            f"; 確認用フォルダ={workbook_path.parent}; "
            f"Excelコンテ={workbook_path.name}; "
            "動画生成前に利用者の確認・承認が必要です"
        )
    return (
        f"生成={generated}枚、残り={len(missing)}枚: "
        f"{run_dir / 'images'}{workbook_note}"
    )


def build_workbook_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    _require_storyboard_images(storyboard, run_dir)
    assets = load_manifest(run_dir / "manifest.json")
    destination = next_storyboard_workbook(run_dir)
    _, japanese_html, english_html = _build_storyboard_review_bundle(
        storyboard,
        run_dir,
        assets,
        destination,
    )
    return (
        f"確認用フォルダ: {destination.parent}\n"
        f"正式Excelコンテ: {destination.name}\n"
        f"Excelなし用: {japanese_html.name}, {english_html.name}\n"
        "Excelコンテを開いて全ショットを確認してください。"
        "利用者の承認前に動画生成へ進まないでください。"
    )


def approve_workbook_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    _require_storyboard_images(storyboard, run_dir)
    workbook_path = _workbook_path(run_dir)
    try:
        destination = approve_workbook(storyboard, workbook_path)
    except PermissionError as error:
        raise RuntimeError(
            "Excelコンテが開かれているため承認状態を保存できません。"
            "Excelで保存してから閉じ、AIエージェントへ「閉じた」と"
            "返してください。"
        ) from error
    return f"Excelコンテ承認済み: {destination}"


def render_videos_command(
    run_dir: Path,
    video_model: str | None = None,
    limit: int | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    _require_approved_workbook(storyboard, run_dir)
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
    source = _require_approved_workbook(storyboard, run_dir)
    destination = next_video_review_workbook(run_dir)
    create_video_workbook(storyboard, source, run_dir, destination)
    japanese_html = create_review_html(
        storyboard,
        run_dir,
        review_html_path(destination, "ja"),
        language="ja",
        video_frames=True,
    )
    english_html = create_review_html(
        storyboard,
        run_dir,
        review_html_path(destination, "en"),
        language="en",
        video_frames=True,
    )
    return (
        f"動画確認用フォルダ: {destination.parent}\n"
        f"正式Excel: {destination.name}\n"
        f"Excelなし用: {japanese_html.name}, {english_html.name}"
    )


def reveal_artifact_command(
    run_dir: Path,
    artifact: str,
    language: str = "ja",
    dry_run: bool = False,
) -> str:
    target = artifact_for_reveal(
        run_dir,
        artifact,
        language=language,
    )
    if not target.is_file():
        raise FileNotFoundError(
            f"表示する成果物がまだありません: {target}"
        )
    result = reveal_in_file_manager(target, dry_run=dry_run)
    if dry_run:
        if language == "en":
            return f"DRY RUN: The folder was not opened. Would select: {target}"
        return f"確認モード: フォルダは開いていません。選択予定: {target}"
    if language == "en":
        if result.opened:
            action = (
                "Double-click the selected file. When it opens, reply: Opened."
                if result.selected
                else (
                    f"Find {target.name} in that folder and double-click it. "
                    "When it opens, reply: Opened."
                )
            )
            return (
                f"Folder opened: {target.parent}\n"
                f"File: {target.name}\n{action}"
            )
        return (
            "ACTION_REQUIRED: This environment could not open the folder.\n"
            f"Folder: {target.parent}\nFile: {target.name}\n"
            "Open that folder, then double-click the named file."
        )
    if result.opened:
        action = (
            "青く選択されたファイルをダブルクリックしてください。"
            "開いたら「開いた」と返してください。"
            if result.selected
            else (
                f"フォルダ内の「{target.name}」をダブルクリックしてください。"
                "開いたら「開いた」と返してください。"
            )
        )
        return (
            f"フォルダを開きました: {target.parent}\n"
            f"ファイル: {target.name}\n{action}"
        )
    return (
        "ACTION_REQUIRED: この環境からフォルダを開けませんでした。\n"
        f"フォルダ: {target.parent}\nファイル: {target.name}\n"
        "そのフォルダを開き、同じ名前のファイルをダブルクリックしてください。"
    )


def extract_corrections_command(
    workbook_path: Path,
    output_path: Path | None = None,
) -> str:
    workbook_path = workbook_path.resolve()
    destination = (
        output_path.resolve()
        if output_path
        else (
            workbook_path.parent.parent
            / f"corrections_{workbook_path.stem}.json"
            if workbook_path.parent.name == "review"
            else workbook_path.parent / "corrections.json"
        )
    )
    extract_corrections(workbook_path, destination)
    return str(destination)
