from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.pipeline import (  # noqa: E402
    apply_corrections_command,
    approve_character_command,
    approve_workbook_command,
    archive_production_command,
    build_video_workbook_command,
    build_workbook_command,
    character_status_command,
    completion_status_command,
    create_command,
    create_storyboard_in_run_command,
    extract_corrections_command,
    finalize_video_command,
    finish_production_command,
    prepare_motion_keyframes_command,
    prepare_tutorial_command,
    register_character_command,
    render_images_command,
    render_videos_command,
    reveal_artifact_command,
    show_sample_command,
    validate_character_registry_command,
)
from video_storyboard.updates import (  # noqa: E402
    check_for_updates,
    format_update_status,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ストーリーと素材から3秒単位のExcel絵コンテを作成します。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    tutorial = subparsers.add_parser(
        "prepare-tutorial",
        help="YouTube URLに対応するNijiUnit公式教材をホームページから直接読む",
    )
    tutorial.add_argument("--youtube-url", required=True)
    tutorial.add_argument("--language", choices=("ja", "en"), default="ja")
    tutorial.add_argument(
        "--write-sample-story",
        action="store_true",
        help="利用者の確認後、公式の公開ストーリーをinput/sample_story.mdへ保存",
    )
    tutorial.add_argument("--input-dir", type=Path, default=ROOT / "input")

    sample = subparsers.add_parser(
        "show-sample",
        help="同梱の完成動画または承認済みExcelコンテを実物で表示する",
    )
    sample.add_argument(
        "--artifact",
        choices=("video", "storyboard", "review-html"),
        default="video",
    )
    sample.add_argument("--language", choices=("ja", "en"), default="ja")
    sample.add_argument("--dry-run", action="store_true")

    update = subparsers.add_parser(
        "check-update",
        help="GitHubと現在版を比較する（更新は行わない）",
    )
    update.add_argument("--language", choices=("ja", "en"), default="ja")

    create = subparsers.add_parser("create", help="素材を解析して3秒構成JSONを作成")
    create.add_argument("--input-dir", type=Path, default=ROOT / "input")
    create.add_argument("--output-root", type=Path, default=ROOT / "output" / "storyboard")
    create.add_argument("--story-model", default=None)
    create.add_argument(
        "--aspect-ratio",
        choices=("9:16", "16:9"),
        required=True,
        help="利用者が選んだYouTube Shorts向け9:16、または通常動画向け16:9",
    )
    create.add_argument(
        "--character-registry-dir",
        type=Path,
        default=ROOT / "characters",
    )

    resume_create = subparsers.add_parser(
        "create-storyboard",
        help="Generate storyboard JSON in a run that already has prepared references",
    )
    resume_create.add_argument("--input-dir", type=Path, default=ROOT / "input")
    resume_create.add_argument("--run-dir", type=Path, required=True)
    resume_create.add_argument("--story-model", default=None)
    resume_create.add_argument(
        "--character-registry-dir",
        type=Path,
        default=ROOT / "characters",
    )

    render = subparsers.add_parser(
        "render-images", help="構成JSONから各シートのメイン画像を生成"
    )
    render.add_argument("--run-dir", type=Path, required=True)
    render.add_argument("--image-model", default=None)
    render.add_argument(
        "--character-registry-dir",
        type=Path,
        default=ROOT / "characters",
        help="人物台帳。既定値はリポジトリ直下のcharacters",
    )
    render.add_argument(
        "--limit",
        type=int,
        default=None,
        help="今回生成する最大枚数。省略時は未生成画像をすべて生成",
    )

    workbook = subparsers.add_parser(
        "build-workbook",
        help="全メイン画像を入れた正式レビュー用Excelコンテを作成",
    )
    workbook.add_argument("--run-dir", type=Path, required=True)

    approve = subparsers.add_parser(
        "approve-workbook",
        help="利用者が確認済みのExcelコンテを承認状態にする",
    )
    approve.add_argument("--run-dir", type=Path, required=True)

    videos = subparsers.add_parser(
        "render-videos",
        help="Generate one 3-second video clip per storyboard shot",
    )
    videos.add_argument("--run-dir", type=Path, required=True)
    videos.add_argument("--video-model", default=None)
    videos.add_argument(
        "--character-registry-dir",
        type=Path,
        default=ROOT / "characters",
        help="人物台帳。既定値はリポジトリ直下のcharacters",
    )
    videos.add_argument("--limit", type=int, default=None)

    character_registry = subparsers.add_parser(
        "validate-characters",
        help="キャラクター台帳と全基準画像を検証し、ハッシュを固定",
    )
    character_registry.add_argument(
        "--registry-dir",
        type=Path,
        default=ROOT / "characters",
    )

    character_status = subparsers.add_parser(
        "character-status",
        help="絵コンテの登場人物を承認済み・確認待ち・未登録に分ける",
    )
    character_status.add_argument("--run-dir", type=Path, required=True)
    character_status.add_argument(
        "--registry-dir", type=Path, default=ROOT / "characters"
    )

    register_character = subparsers.add_parser(
        "register-character",
        help="権利確認済みの仕様JSONと素材からキャラクター確認資料を作る",
    )
    register_character.add_argument("--spec", type=Path, required=True)
    register_character.add_argument(
        "--registry-dir", type=Path, default=ROOT / "characters"
    )

    approve_character = subparsers.add_parser(
        "approve-character",
        help="利用者が確認したキャラクター版を有効化する",
    )
    approve_character.add_argument("--id", required=True)
    approve_character.add_argument("--version", required=True)
    approve_character.add_argument(
        "--registry-dir", type=Path, default=ROOT / "characters"
    )

    prepare_motions = subparsers.add_parser(
        "prepare-motions",
        help="台帳の3秒動作動画から開始・中間・終了キーフレームを抽出",
    )
    prepare_motions.add_argument(
        "--registry-dir",
        type=Path,
        default=ROOT / "characters",
    )
    prepare_motions.add_argument("--overwrite", action="store_true")

    final_video = subparsers.add_parser(
        "finalize-video",
        help="Concatenate all 3-second clips into the final video",
    )
    final_video.add_argument("--run-dir", type=Path, required=True)

    finish = subparsers.add_parser(
        "finish-production",
        help="承認済み動画へ音声・音楽・字幕を反映し完成確認資料まで作る",
    )
    finish.add_argument("--run-dir", type=Path, required=True)
    finish.add_argument("--generate-speech", action="store_true")
    finish.add_argument("--voice-config", type=Path, default=None)
    finish.add_argument("--music-file", type=Path, default=None)
    finish.add_argument("--music-rights-confirmed", action="store_true")
    finish.add_argument("--music-volume", type=float, default=0.12)
    finish.add_argument("--no-subtitles", action="store_true")

    video_workbook = subparsers.add_parser(
        "build-video-workbook",
        help="Embed the nine extracted video frames into every shot sheet",
    )
    video_workbook.add_argument("--run-dir", type=Path, required=True)

    corrections = subparsers.add_parser(
        "extract-corrections", help="Excelに記入された訂正指示をJSONへ抽出"
    )
    corrections.add_argument("--workbook", type=Path, required=True)
    corrections.add_argument("--output", type=Path, default=None)

    apply_corrections = subparsers.add_parser(
        "apply-corrections",
        help="Excelの訂正指示を絵コンテへ反映し、新版確認物の準備をする",
    )
    apply_corrections.add_argument("--run-dir", type=Path, required=True)
    apply_corrections.add_argument("--workbook", type=Path, default=None)
    apply_corrections.add_argument("--story-model", default=None)
    apply_corrections.add_argument(
        "--character-registry-dir",
        type=Path,
        default=ROOT / "characters",
    )

    reveal = subparsers.add_parser(
        "reveal-artifact",
        help="成果物のフォルダを開き、対象ファイルを選択",
    )
    reveal.add_argument("--run-dir", type=Path, required=True)
    reveal.add_argument(
        "--artifact",
        choices=(
            "storyboard",
            "review-html",
            "final-video",
            "video-review",
            "ai-record",
        ),
        required=True,
    )
    reveal.add_argument("--language", choices=("ja", "en"), default="ja")
    reveal.add_argument("--dry-run", action="store_true")

    completion = subparsers.add_parser(
        "completion-status",
        help="前回会話が終わっても残る完成確認待ちとhistoryを確認する",
    )
    completion.add_argument(
        "--output-root", type=Path, default=ROOT / "output" / "storyboard"
    )
    completion.add_argument("--history-root", type=Path, default=ROOT / "history")
    completion.add_argument(
        "--language",
        choices=("ja", "en"),
        default="ja",
        help="他の案内コマンドと同じ指定を受け付けます（JSON出力は共通です）",
    )

    archive = subparsers.add_parser(
        "archive-production",
        help="完成確認後、制作一式をローカルhistoryへ移す",
    )
    archive.add_argument("--run-dir", type=Path, required=True)
    archive.add_argument("--input-dir", type=Path, default=ROOT / "input")
    archive.add_argument("--history-root", type=Path, default=ROOT / "history")
    archive.add_argument("--confirmation", required=True)
    archive.add_argument("--title", default=None)

    return parser


def _dispatch(args: argparse.Namespace) -> str:
    if args.command == "prepare-tutorial":
        result = prepare_tutorial_command(
            youtube_url=args.youtube_url,
            language=args.language,
            sample_story_input_dir=(
                args.input_dir if args.write_sample_story else None
            ),
        )
    elif args.command == "show-sample":
        result = show_sample_command(
            args.artifact,
            args.language,
            args.dry_run,
        )
    elif args.command == "check-update":
        result = format_update_status(check_for_updates(ROOT), args.language)
    elif args.command == "create":
        result = create_command(
            input_dir=args.input_dir,
            output_root=args.output_root,
            story_model=args.story_model,
            character_registry_dir=args.character_registry_dir,
            aspect_ratio=args.aspect_ratio,
        )
    elif args.command == "create-storyboard":
        result = create_storyboard_in_run_command(
            input_dir=args.input_dir,
            run_dir=args.run_dir,
            story_model=args.story_model,
            character_registry_dir=args.character_registry_dir,
        )
    elif args.command == "render-images":
        result = render_images_command(
            run_dir=args.run_dir,
            image_model=args.image_model,
            limit=args.limit,
            character_registry_dir=args.character_registry_dir,
        )
    elif args.command == "build-workbook":
        result = build_workbook_command(run_dir=args.run_dir)
    elif args.command == "approve-workbook":
        result = approve_workbook_command(run_dir=args.run_dir)
    elif args.command == "render-videos":
        result = render_videos_command(
            run_dir=args.run_dir,
            video_model=args.video_model,
            limit=args.limit,
            character_registry_dir=args.character_registry_dir,
        )
    elif args.command == "validate-characters":
        result = validate_character_registry_command(args.registry_dir)
    elif args.command == "character-status":
        result = character_status_command(args.run_dir, args.registry_dir)
    elif args.command == "register-character":
        result = register_character_command(args.spec, args.registry_dir)
    elif args.command == "approve-character":
        result = approve_character_command(
            args.registry_dir,
            args.id,
            args.version,
        )
    elif args.command == "prepare-motions":
        result = prepare_motion_keyframes_command(
            args.registry_dir,
            args.overwrite,
        )
    elif args.command == "finalize-video":
        result = finalize_video_command(run_dir=args.run_dir)
    elif args.command == "finish-production":
        result = finish_production_command(
            args.run_dir,
            generate_speech=args.generate_speech,
            voice_config=args.voice_config,
            music_file=args.music_file,
            music_rights_confirmed=args.music_rights_confirmed,
            music_volume=args.music_volume,
            subtitles=not args.no_subtitles,
        )
    elif args.command == "build-video-workbook":
        result = build_video_workbook_command(run_dir=args.run_dir)
    elif args.command == "extract-corrections":
        result = extract_corrections_command(
            workbook_path=args.workbook,
            output_path=args.output,
        )
    elif args.command == "apply-corrections":
        result = apply_corrections_command(
            run_dir=args.run_dir,
            workbook_path=args.workbook,
            story_model=args.story_model,
            character_registry_dir=args.character_registry_dir,
        )
    elif args.command == "reveal-artifact":
        result = reveal_artifact_command(
            run_dir=args.run_dir,
            artifact=args.artifact,
            language=args.language,
            dry_run=args.dry_run,
        )
    elif args.command == "completion-status":
        result = completion_status_command(args.output_root, args.history_root)
    elif args.command == "archive-production":
        result = archive_production_command(
            args.run_dir,
            args.input_dir,
            args.history_root,
            args.confirmation,
            args.title,
        )
    else:
        raise AssertionError(args.command)
    return result


def main() -> int:
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure:
                reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    try:
        result = _dispatch(args)
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError) as error:
        print(f"ACTION_REQUIRED: {error}")
        return 2

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
