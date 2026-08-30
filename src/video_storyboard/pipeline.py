from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .artifacts import (
    artifact_for_reveal,
    current_storyboard_workbook,
    is_directly_viewable,
    next_storyboard_workbook,
    next_video_review_workbook,
    open_in_default_app,
    reveal_in_file_manager,
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
from .schema import Storyboard
from .settings import CHARACTER_REGISTRY_DIR
from .video import concatenate_clips, inspect_video, render_video_shots
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
    run_dir = _next_run_dir(output_root.resolve())
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
        [name for shot in storyboard.shots for name in shot.characters],
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
    completed = render_video_shots(
        storyboard=storyboard,
        run_dir=run_dir,
        profile=guidance.profile,
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
    destination = run_dir / "final" / f"story_video_{run_dir.name}.mp4"
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
    if is_directly_viewable(target):
        result = open_in_default_app(target, dry_run=dry_run)
        if dry_run:
            if language == "en":
                return f"DRY RUN: Would open the review artifact itself: {target}"
            return f"確認モード: 確認するファイルそのものを開く予定です: {target}"
        if result.opened:
            if language == "en":
                return (
                    f"Opened the review artifact itself: {target.name}\n"
                    "Review the window that just opened."
                )
            return (
                f"確認するファイルそのものを開きました: {target.name}\n"
                "いま開いた画面を確認してください。"
            )
        if language == "en":
            return (
                "ACTION_REQUIRED: This environment could not open the review artifact.\n"
                f"File: {target}"
            )
        return (
            "ACTION_REQUIRED: この環境から確認するファイルを開けませんでした。\n"
            f"ファイル: {target}"
        )
    result = reveal_in_file_manager(target, dry_run=dry_run)
    if dry_run:
        if language == "en":
            return f"DRY RUN: The folder was not opened. Would select: {target}"
        return f"確認モード: フォルダは開いていません。選択予定: {target}"
    if language == "en":
        if result.opened:
            action = (
                f"Double-click {target.name}. When it opens, reply: Opened."
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
            f"表示された「{target.name}」をダブルクリックしてください。"
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
    result = reveal_in_file_manager(target, dry_run=dry_run)
    if dry_run:
        return f"確認モード: 選択予定の公開サンプル: {target}"
    if result.opened:
        if language == "en":
            return (
                f"Sample folder opened: {target.parent}\n"
                f"Double-click the displayed file: {target.name}"
            )
        return (
            f"サンプルのフォルダーを開きました: {target.parent}\n"
            f"表示された「{target.name}」をダブルクリックしてください。"
        )
    return f"サンプル: {target}"


def import_input_assets_command(source: Path, input_dir: Path) -> str:
    copied, unchanged = import_assets(source, input_dir)
    lines = ["素材をinputへ安全に取り込みました。"]
    lines.extend(f"追加: {path.name}" for path in copied)
    lines.extend(f"既に同じ内容: {path.name}" for path in unchanged)
    return "\n".join(lines)


def _next_storyboard_json_revision(run_dir: Path) -> tuple[int, Path]:
    revisions = []
    for path in run_dir.glob("storyboard_r*.json"):
        match = re.fullmatch(r"storyboard_r(\d{3})\.json", path.name)
        if match:
            revisions.append(int(match.group(1)))
    revision = max(revisions, default=1) + 1
    return revision, run_dir / f"storyboard_r{revision:03d}.json"


def _shot_number_from_sheet(sheet: str) -> int | None:
    match = re.match(r"S(\d{3})", sheet)
    return int(match.group(1)) if match else None


def apply_corrections_command(
    run_dir: Path,
    workbook_path: Path | None = None,
    story_model: str | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> str:
    """Apply Excel corrections and invalidate only affected review images."""
    run_dir = run_dir.resolve()
    storyboard_path = run_dir / "storyboard.json"
    storyboard = _load_storyboard(run_dir)
    guidance = _load_pinned_guidance(run_dir, storyboard)
    workbook_path = (
        workbook_path.resolve() if workbook_path else _workbook_path(run_dir)
    )
    corrections_path = run_dir / f"corrections_{workbook_path.stem}.json"
    extract_corrections(workbook_path, corrections_path)
    correction_data = json.loads(corrections_path.read_text(encoding="utf-8"))
    requested = []
    missing_instruction = []
    for item in correction_data["corrections"]:
        instruction = str(item.get("instruction") or "").strip()
        status = str(item.get("review_status") or "").strip()
        if status == "修正必要" and not instruction:
            missing_instruction.append(str(item.get("sheet") or ""))
        if instruction:
            requested.append(item)
    if missing_instruction:
        raise RuntimeError(
            "修正内容が空欄です。黄色い訂正指示欄へ、直したい内容を書いてください: "
            + ", ".join(missing_instruction)
        )
    if not requested:
        raise RuntimeError("反映する訂正指示がありません。")

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

    revision, revision_path = _next_storyboard_json_revision(run_dir)
    first_revision = run_dir / "storyboard_r001.json"
    if not first_revision.exists():
        shutil.copy2(storyboard_path, first_revision)
    serialized = revised.model_dump_json(indent=2)
    revision_path.write_text(serialized, encoding="utf-8")
    storyboard_path.write_text(serialized, encoding="utf-8")

    affected = {
        number
        for item in requested
        if (number := _shot_number_from_sheet(str(item.get("sheet") or "")))
    }
    if any(str(item.get("revision_scope")) == "大規模" for item in requested):
        affected = {shot.shot_number for shot in revised.shots}
    rejected_dir = run_dir / "rejected" / f"before_storyboard_r{revision:03d}"
    invalidated: list[str] = []
    for number in sorted(affected):
        image = run_dir / "images" / f"shot_{number:03d}.png"
        if not image.is_file():
            continue
        rejected_dir.mkdir(parents=True, exist_ok=True)
        backup = rejected_dir / image.name
        shutil.copy2(image, backup)
        image.unlink()
        invalidated.append(image.name)

    log_path = run_dir / "revision_log.jsonl"
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "revision": revision,
                    "source_workbook": workbook_path.name,
                    "corrections_file": corrections_path.name,
                    "affected_shots": sorted(affected),
                    "invalidated_images": invalidated,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return (
        f"訂正をstoryboard_r{revision:03d}.jsonへ反映しました。\n"
        f"再生成が必要な画像: {', '.join(invalidated) or 'なし'}\n"
        "次は不足画像を生成してください。全画像が揃うと新版Excelを作成できます。"
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
