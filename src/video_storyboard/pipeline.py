from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .artifacts import (
    artifact_display_name,
    artifact_for_reveal,
    current_storyboard_workbook,
    next_storyboard_workbook,
    next_video_review_workbook,
    prepare_review_copy,
    reveal_handoff_message,
    reveal_in_file_manager,
    review_copy_path,
    review_html_path,
)
from .assets import (
    import_assets,
    load_manifest,
    prepare_assets,
    read_story,
    save_manifest,
)
from .character_registration import (
    approve_character,
    character_status,
    register_character,
)
from .character_registry import (
    CharacterRegistry,
    require_resolved_character_names,
)
from .gemini_service import GeminiService
from .history import (
    archive_production,
    completion_status,
    mark_completion_review_pending,
)
from .knowledge import (
    ensure_production_allowed,
    load_builtin_guidance,
    load_run_guidance,
    snapshot_guidance,
)
from .motion_assets import prepare_motion_keyframes
from .review_html import create_review_html
from .revisions import create_run_revision
from .run_versions import allocate_run_dir, run_version_name
from .schema import Storyboard
from .settings import CHARACTER_REGISTRY_DIR
from .video import (
    concatenate_clips,
    extract_source_frame,
    inspect_video,
    render_video_shots,
    source_asset_path,
)
from .website_tutorial import (
    fetch_tutorial_page,
    format_tutorial_page,
    write_sample_story,
)
from .workbook import (
    approve_workbook,
    create_video_workbook,
    create_workbook,
    extract_corrections,
    workbook_review_issues,
)


def _current_production_guidance():
    guidance = load_builtin_guidance()
    ensure_production_allowed(guidance, "ja")
    if guidance.warning:
        print(f"[warning] {guidance.warning}")
    return guidance


def _load_storyboard(run_dir: Path) -> Storyboard:
    return Storyboard.model_validate_json(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )


def _require_storyboard_matches_guidance(storyboard, guidance) -> None:
    selected_aspect_ratio = guidance.profile.media.aspect_ratio
    if storyboard.aspect_ratio != selected_aspect_ratio:
        raise RuntimeError(
            "制作開始時に固定した映像比率とstoryboard.jsonの映像比率が"
            "一致しません。制作途中では映像比率を変更できません。"
            "別の映像比率で作る場合は、新しい制作として最初から開始してください。"
        )


def _load_pinned_guidance(run_dir: Path, storyboard: Storyboard):
    guidance = load_run_guidance(run_dir)
    _require_storyboard_matches_guidance(storyboard, guidance)
    return guidance


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
    aspect_ratio: str | None = None,
) -> str:
    input_dir = input_dir.resolve()
    if aspect_ratio is None:
        raise RuntimeError(
            "制作開始前に、利用者へ縦長9:16または横長16:9を確認し、"
            "--aspect-ratioで明示してください。"
        )
    guidance = _current_production_guidance().for_aspect_ratio(aspect_ratio)
    run_dir = allocate_run_dir(output_root.resolve())
    snapshot_guidance(guidance, run_dir)
    reference_dir = run_dir / "references"
    reference_dir.mkdir()

    print(f"[1/3] ストーリーを読み込み: {input_dir}")
    story_path, story = read_story(input_dir)
    print("[2/3] 参照素材を準備")
    assets = prepare_assets(input_dir, reference_dir)
    save_manifest(assets, story_path, run_dir / "manifest.json")

    print("[3/3] Geminiで3秒構成を生成")
    service = GeminiService(
        profile=guidance.profile,
        story_model=story_model,
    )
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    storyboard = service.create_storyboard(
        story,
        assets,
        input_dir,
        character_registry,
    )
    _require_storyboard_matches_guidance(storyboard, guidance)
    (run_dir / "storyboard.json").write_text(
        storyboard.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(
        f"構成完了: {len(storyboard.shots)}シート / "
        f"{storyboard.total_duration_seconds}秒"
    )
    print(f"使用したホームページ指示: {guidance.manifest.knowledge_version}")
    print(
        "映像比率: "
        f"{guidance.profile.media.aspect_ratio} "
        f"({guidance.profile.media.width}x{guidance.profile.media.height})"
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
    _current_production_guidance()
    _, story = read_story(input_dir)
    assets = load_manifest(run_dir / "manifest.json")
    guidance = load_run_guidance(run_dir)
    service = GeminiService(
        profile=guidance.profile,
        story_model=story_model,
    )
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    storyboard = service.create_storyboard(
        story,
        assets,
        input_dir,
        character_registry,
    )
    _require_storyboard_matches_guidance(storyboard, guidance)
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
    _current_production_guidance()
    storyboard = _load_storyboard(run_dir)
    assets = load_manifest(run_dir / "manifest.json")
    guidance = _load_pinned_guidance(run_dir, storyboard)
    character_registry = CharacterRegistry.load_optional(character_registry_dir)
    if character_registry:
        issues = character_registry.validate()
        if issues:
            raise RuntimeError(
                "Invalid character registry:\n" + "\n".join(issues)
            )
    require_resolved_character_names(
        character_registry,
        [
            name
            for shot in storyboard.shots
            if shot.production_mode == "generated_video"
            for name in shot.characters
        ],
    )
    service = GeminiService(
        profile=guidance.profile,
        image_model=image_model,
    )
    generated = 0
    for index, shot in enumerate(storyboard.shots):
        destination = run_dir / "images" / f"shot_{shot.shot_number:03d}.png"
        if destination.exists():
            print(f"[skip] S{shot.shot_number:03d}: 生成済み")
            continue
        if shot.production_mode == "source_video":
            source = source_asset_path(shot, assets)
            extract_source_frame(
                source,
                shot.source_start_seconds or 0.0,
                destination,
                guidance.profile.media,
            )
            print(
                f"[source] S{shot.shot_number:03d}: "
                f"{shot.source_asset} の実写フレームを使用"
            )
            continue
        previous = storyboard.shots[index - 1] if index else None
        if (
            shot.continuity_start_mode == "previous_final_frame"
            and previous is not None
            and previous.production_mode == "source_video"
        ):
            source = source_asset_path(previous, assets)
            extract_source_frame(
                source,
                previous.source_end_seconds or 0.0,
                destination,
                guidance.profile.media,
            )
            print(
                f"[source-transition] S{shot.shot_number:03d}: "
                "直前の実写最終フレームを使用"
            )
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
    _load_pinned_guidance(run_dir, storyboard)
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
    _load_pinned_guidance(run_dir, storyboard)
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
    guidance = _load_pinned_guidance(run_dir, storyboard)
    _require_approved_workbook(storyboard, run_dir)
    _current_production_guidance()
    assets = load_manifest(run_dir / "manifest.json")
    completed = render_video_shots(
        storyboard=storyboard,
        run_dir=run_dir,
        profile=guidance.profile,
        assets=assets,
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


def character_status_command(run_dir: Path, registry_dir: Path) -> str:
    status = character_status(_load_storyboard(run_dir.resolve()), registry_dir.resolve())
    return json.dumps(status, ensure_ascii=False, indent=2)


def register_character_command(spec_path: Path, registry_dir: Path) -> str:
    profile, japanese_html, english_html = register_character(
        spec_path.resolve(), registry_dir.resolve()
    )
    return (
        "キャラクターの確認用資料を作りました。まだ登録は確定していません。\n"
        f"日本語確認ページ: {japanese_html}\n"
        f"English review page: {english_html}\n"
        f"確認待ちプロフィール: {profile}"
    )


def approve_character_command(
    registry_dir: Path,
    character_id: str,
    version: str,
) -> str:
    profile = approve_character(registry_dir.resolve(), character_id, version)
    return f"キャラクターを承認して台帳へ登録しました: {profile}"


def prepare_motion_keyframes_command(
    registry_dir: Path,
    overwrite: bool = False,
) -> str:
    generated = prepare_motion_keyframes(registry_dir.resolve(), overwrite)
    return f"motion_keyframes_generated={len(generated)}: {registry_dir.resolve()}"


def finalize_video_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    guidance = _load_pinned_guidance(run_dir, storyboard)
    destination = (
        run_dir / "final" / f"story_video_{run_version_name(run_dir)}.mp4"
    )
    concatenate_clips(storyboard, run_dir, destination, guidance.profile.media)
    metadata = inspect_video(destination)
    (destination.parent / "video_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(destination)


def build_video_workbook_command(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    _load_pinned_guidance(run_dir, storyboard)
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
    mark_completion_review_pending(run_dir, destination)
    return (
        f"動画確認用フォルダ: {destination.parent}\n"
        f"正式Excel: {destination.name}\n"
        f"Excelなし用: {japanese_html.name}, {english_html.name}"
    )


def completion_status_command(output_root: Path, history_root: Path) -> str:
    return json.dumps(
        completion_status(output_root.resolve(), history_root.resolve()),
        ensure_ascii=False,
        indent=2,
    )


def archive_production_command(
    run_dir: Path,
    input_dir: Path,
    history_root: Path,
    confirmation: str,
    title: str | None = None,
) -> str:
    archive = archive_production(
        run_dir,
        input_dir,
        history_root,
        confirmation,
        title,
    )
    return (
        f"制作一式をhistoryへ移しました: {archive}\n"
        f"修正するときは、この中のrunフォルダーから再開できます: {archive / 'run'}"
    )


def _run_project_script(script_name: str, arguments: list[str]) -> str:
    script = Path(__file__).resolve().parents[2] / "scripts" / script_name
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = "\n".join(result.stderr.splitlines()[-30:]) or result.stdout
        raise RuntimeError(f"{script_name}に失敗しました。\n{detail}")
    return result.stdout.strip()


def finish_production_command(
    run_dir: Path,
    *,
    generate_speech: bool = False,
    voice_config: Path | None = None,
    music_file: Path | None = None,
    music_rights_confirmed: bool = False,
    music_volume: float = 0.12,
    subtitles: bool = True,
) -> str:
    """Run the local audio/subtitle/final-review sequence as one guarded step."""
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    _load_pinned_guidance(run_dir, storyboard)
    _require_approved_workbook(storyboard, run_dir)
    for shot in storyboard.shots:
        clip = run_dir / "video" / "clips" / f"shot_{shot.shot_number:03d}.mp4"
        if not clip.is_file():
            raise FileNotFoundError(f"動画クリップがありません: {clip}")

    has_speech = any(shot.dialogue or shot.narration for shot in storyboard.shots)
    if has_speech and not generate_speech:
        raise RuntimeError(
            "台詞またはナレーションがあります。音声生成にはAPI利用があるため、"
            "説明と利用者の確認後に--generate-speechを付けてください。"
        )
    if music_file and not music_rights_confirmed:
        raise RuntimeError(
            "音楽の利用権が未確認です。利用できる音源だと本人が確認した後だけ"
            "--music-rights-confirmedを付けてください。"
        )
    if not 0 <= music_volume <= 1:
        raise ValueError("music volume must be between 0 and 1")

    if has_speech:
        arguments = ["--run-dir", str(run_dir)]
        if voice_config:
            arguments.extend(["--voice-config", str(voice_config.resolve())])
        _run_project_script("generate_storyboard_tts.py", arguments)

    soundtrack_arguments = ["--run-dir", str(run_dir)]
    if music_file:
        source = music_file.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        music_dir = run_dir / "audio" / "source_music"
        music_dir.mkdir(parents=True, exist_ok=True)
        copied = music_dir / source.name
        if copied.exists() and copied.read_bytes() != source.read_bytes():
            copied = music_dir / f"{source.stem}_{len(list(music_dir.iterdir())) + 1}{source.suffix}"
        if not copied.exists():
            shutil.copy2(source, copied)
        soundtrack_arguments.extend(
            ["--music-file", str(copied), "--music-volume", str(music_volume)]
        )
    _run_project_script("rebuild_clean_soundtrack.py", soundtrack_arguments)
    if subtitles and has_speech:
        _run_project_script(
            "apply_storyboard_subtitles.py",
            ["--run-dir", str(run_dir)],
        )
    final_video = finalize_video_command(run_dir)
    review_bundle = build_video_workbook_command(run_dir)
    return (
        f"完成動画: {final_video}\n"
        f"確認資料: {review_bundle}\n"
        "完成確認待ちとして保存しました。会話が終わっても次回再開できます。"
    )


def reveal_artifact_command(
    run_dir: Path,
    artifact: str,
    language: str = "ja",
    dry_run: bool = False,
    display_name: str | None = None,
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
    beginner_name = display_name or artifact_display_name(
        artifact,
        target.suffix,
        language,
    )
    if dry_run:
        target = review_copy_path(target, beginner_name)
        return reveal_handoff_message(
            target,
            None,
            language=language,
            dry_run=True,
        )
    target = prepare_review_copy(target, beginner_name)
    result = reveal_in_file_manager(target)
    return reveal_handoff_message(target, result, language=language)


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


def show_sample_command(
    sample: str = "video",
    language: str = "ja",
    dry_run: bool = False,
) -> str:
    root = Path(__file__).resolve().parents[2] / "examples" / "space-friends"
    names = {
        "video": "demo.mp4",
        "storyboard": "storyboard_approved.xlsx",
        "review-html": f"storyboard_approved_review.{language}.html",
    }
    target = root / names[sample]
    if not target.is_file():
        raise FileNotFoundError(f"公開サンプルがありません: {target}")
    if dry_run:
        return reveal_handoff_message(
            target,
            None,
            language=language,
            dry_run=True,
        )
    result = reveal_in_file_manager(target)
    return reveal_handoff_message(target, result, language=language)


def import_input_assets_command(source: Path, input_dir: Path) -> str:
    copied, unchanged = import_assets(source, input_dir)
    lines = ["素材をinputへ安全に取り込みました。"]
    lines.extend(f"追加: {path.name}" for path in copied)
    lines.extend(f"既に同じ内容: {path.name}" for path in unchanged)
    return "\n".join(lines)


def _shot_number_from_sheet(sheet: str) -> int | None:
    match = re.match(r"S(\d{3})", sheet)
    return int(match.group(1)) if match else None


def _validate_correction_data(
    correction_data: object,
    storyboard: Storyboard,
) -> tuple[dict, list[dict]]:
    if not isinstance(correction_data, dict):
        raise RuntimeError("訂正JSONはオブジェクトである必要があります。")
    corrections = correction_data.get("corrections")
    if not isinstance(corrections, list):
        raise RuntimeError("訂正JSONにcorrections配列がありません。")
    requested: list[dict] = []
    missing_instruction: list[str] = []
    invalid_sheets: list[str] = []
    invalid_scopes: list[str] = []
    valid_shots = {shot.shot_number for shot in storyboard.shots}
    for raw_item in corrections:
        if not isinstance(raw_item, dict):
            raise RuntimeError("correctionsの各項目はオブジェクトである必要があります。")
        item = dict(raw_item)
        instruction = str(item.get("instruction") or "").strip()
        status = str(item.get("review_status") or "").strip()
        if status == "修正必要" and not instruction:
            missing_instruction.append(str(item.get("sheet") or ""))
        if instruction:
            sheet = str(item.get("sheet") or "").strip()
            number = _shot_number_from_sheet(sheet)
            if number is None or number not in valid_shots:
                invalid_sheets.append(sheet or "（シート名なし）")
            scope = str(item.get("revision_scope") or "").strip()
            if scope not in {"小規模", "大規模"}:
                invalid_scopes.append(f"{sheet or '（シート名なし）'}: {scope or '未指定'}")
            requested.append(item)
    if missing_instruction:
        raise RuntimeError(
            "修正内容が空欄です。直したい内容を書いてください: "
            + ", ".join(missing_instruction)
        )
    if invalid_sheets:
        raise RuntimeError(
            "訂正先が現在の絵コンテに存在しません: " + ", ".join(invalid_sheets)
        )
    if invalid_scopes:
        raise RuntimeError(
            "訂正規模は「小規模」または「大規模」を指定してください: "
            + ", ".join(invalid_scopes)
        )
    if not requested:
        raise RuntimeError("反映する訂正指示がありません。")
    return correction_data, requested


def _read_corrections(
    workbook_path: Path,
    corrections_file: Path | None,
    storyboard: Storyboard,
) -> tuple[dict, list[dict], str]:
    if corrections_file is not None:
        source = corrections_file.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        data = json.loads(source.read_text(encoding="utf-8"))
        correction_data, requested = _validate_correction_data(data, storyboard)
        return correction_data, requested, source.name

    with tempfile.TemporaryDirectory(prefix="nijiunit-corrections-") as directory:
        temporary = Path(directory) / "corrections.json"
        extract_corrections(workbook_path, temporary)
        data = json.loads(temporary.read_text(encoding="utf-8"))
    correction_data, requested = _validate_correction_data(data, storyboard)
    return correction_data, requested, workbook_path.name


def _validate_revised_storyboard_scope(
    original: Storyboard,
    revised: Storyboard,
    requested: list[dict],
) -> set[int]:
    large_revision = any(
        str(item.get("revision_scope") or "").strip() == "大規模"
        for item in requested
    )
    if large_revision:
        return {shot.shot_number for shot in revised.shots}

    affected = {
        number
        for item in requested
        if (number := _shot_number_from_sheet(str(item.get("sheet") or "")))
    }
    if len(original.shots) != len(revised.shots):
        raise RuntimeError(
            "小規模訂正でショット数が変わりました。大規模訂正として確認し直してください。"
        )
    original_header = original.model_dump(exclude={"shots"})
    revised_header = revised.model_dump(exclude={"shots"})
    if original_header != revised_header:
        raise RuntimeError(
            "小規模訂正で作品全体の設定が変わりました。大規模訂正として確認し直してください。"
        )
    revised_by_number = {shot.shot_number: shot for shot in revised.shots}
    changed_outside_scope = [
        shot.shot_number
        for shot in original.shots
        if shot.shot_number not in affected
        and revised_by_number[shot.shot_number].model_dump() != shot.model_dump()
    ]
    if changed_outside_scope:
        raise RuntimeError(
            "小規模訂正の対象外ショットが変更されました: "
            + ", ".join(f"S{number:03d}" for number in changed_outside_scope)
        )
    return affected


def _expand_video_continuity_dependents(
    storyboard: Storyboard,
    affected_shots: tuple[int, ...],
) -> tuple[int, ...]:
    expanded = set(affected_shots)
    if not expanded:
        return affected_shots
    for shot in storyboard.shots:
        if (
            shot.production_mode == "generated_video"
            and shot.continuity_start_mode == "previous_final_frame"
            and shot.shot_number - 1 in expanded
        ):
            expanded.add(shot.shot_number)
    return tuple(sorted(expanded))


def _update_revision_record(run_dir: Path, **values: object) -> None:
    record_path = run_dir / "revision_origin.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update(values)
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    history_path = run_dir / "revision_history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    if isinstance(history, list) and history:
        history[-1] = record
        history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def apply_corrections_command(
    run_dir: Path,
    workbook_path: Path | None = None,
    corrections_file: Path | None = None,
    story_model: str | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    """Apply corrections in the next whole vNNN run without changing the source."""
    run_dir = run_dir.resolve()
    storyboard = _load_storyboard(run_dir)
    guidance = _load_pinned_guidance(run_dir, storyboard)
    official_workbook = _workbook_path(run_dir).resolve()
    workbook_path = workbook_path.resolve() if workbook_path else official_workbook
    if not workbook_path.is_file():
        raise FileNotFoundError(workbook_path)
    if workbook_path != official_workbook:
        raise ValueError(
            "訂正にはこの制作版の正式Excelだけを使用できます: "
            f"{official_workbook}"
        )
    correction_data, requested, corrections_source = _read_corrections(
        workbook_path,
        corrections_file,
        storyboard,
    )

    assets = load_manifest(run_dir / "manifest.json")
    registry = CharacterRegistry.load_optional(character_registry_dir)
    service = GeminiService(profile=guidance.profile, story_model=story_model)
    revised = service.revise_storyboard(
        storyboard,
        requested,
        assets,
        registry,
    )
    _require_storyboard_matches_guidance(revised, guidance)
    affected = _validate_revised_storyboard_scope(storyboard, revised, requested)
    revision = create_run_revision(
        run_dir,
        scope="storyboard",
        reason="Excelまたはチャットで受けた絵コンテ訂正を反映",
        affected_shots=tuple(sorted(affected)),
    )
    target_run = revision.target_run
    try:
        rejected_dir = (
            target_run / "rejected" / f"from_{revision.source_version}"
        )
        rejected_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            target_run / "storyboard.json",
            rejected_dir / "storyboard.json",
        )
        (target_run / "storyboard.json").write_text(
            revised.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (target_run / "corrections.json").write_text(
            json.dumps(correction_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        invalidated: list[str] = []
        for number in sorted(affected):
            image = target_run / "images" / f"shot_{number:03d}.png"
            if not image.is_file():
                continue
            image_rejected = rejected_dir / "images" / image.name
            image_rejected.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(image), str(image_rejected))
            invalidated.append(image.name)
        _update_revision_record(
            target_run,
            source_workbook=workbook_path.name,
            corrections_source=corrections_source,
            affected_shots=sorted(affected),
            invalidated_images=invalidated,
        )
    except Exception:
        shutil.rmtree(target_run, ignore_errors=True)
        raise
    return (
        f"訂正を次の制作版へ反映しました: {target_run}\n"
        f"元の制作版は変更せず残しています: {run_dir}\n"
        f"再生成が必要な画像: {', '.join(invalidated) or 'なし'}\n"
        f"次は{revision.target_version}の不足画像を生成してください。"
        "全画像が揃うと同じ版名のExcelコンテを作成できます。"
    )


def revise_run_command(
    run_dir: Path,
    *,
    scope: str,
    reason: str,
    affected_shots: tuple[int, ...] = (),
) -> str:
    """Create the next whole run for a video or audio correction."""
    run_dir = run_dir.resolve()
    if scope not in {"video", "audio"}:
        raise ValueError("revise-runのscopeはvideoまたはaudioです。")
    if scope == "audio" and affected_shots:
        raise ValueError("audio訂正では--shotを指定しません。")
    storyboard = _load_storyboard(run_dir)
    _load_pinned_guidance(run_dir, storyboard)
    _require_approved_workbook(storyboard, run_dir)
    valid_shots = {shot.shot_number for shot in storyboard.shots}
    unknown = sorted(set(affected_shots) - valid_shots)
    if unknown:
        raise ValueError(
            "存在しないショット番号です: "
            + ", ".join(f"S{number:03d}" for number in unknown)
        )
    if scope == "video":
        affected_shots = _expand_video_continuity_dependents(
            storyboard,
            affected_shots,
        )
    revision = create_run_revision(
        run_dir,
        scope=scope,
        reason=reason,
        affected_shots=affected_shots,
    )
    invalidated = (
        ", ".join(f"S{number:03d}" for number in revision.invalidated_shots)
        or "なし"
    )
    return (
        f"次の制作版を作成しました: {revision.target_run}\n"
        f"元の制作版は変更せず残しています: {run_dir}\n"
        f"作り直すショット: {invalidated}"
    )


def prepare_tutorial_command(
    *,
    youtube_url: str,
    language: str = "ja",
    sample_story_input_dir: Path | None = None,
) -> str:
    if language not in {"ja", "en"}:
        raise ValueError("language must be 'ja' or 'en'")
    page = fetch_tutorial_page(youtube_url, language)
    result = format_tutorial_page(page)
    if sample_story_input_dir is None:
        return result

    destination = write_sample_story(page, sample_story_input_dir)
    if language == "ja":
        return (
            f"{result}\n\n"
            "INPUT_SAMPLE_STORY: WRITTEN\n"
            f"参考用サンプルストーリー: {destination.resolve()}\n"
            "本番用ストーリー: input/story.md（別途作成）\n"
            "NijiUnitのキャラクター画像・動画・音声: 配布なし"
        )
    return (
        f"{result}\n\n"
        "INPUT_SAMPLE_STORY: WRITTEN\n"
        f"Reference sample story: {destination.resolve()}\n"
        "Production story: input/story.md (create separately)\n"
        "NijiUnit character images, videos, and audio: not distributed"
    )
