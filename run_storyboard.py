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
    approve_workbook_command,
    build_video_workbook_command,
    build_workbook_command,
    create_command,
    create_storyboard_in_run_command,
    extract_corrections_command,
    finalize_video_command,
    prepare_motion_keyframes_command,
    render_images_command,
    render_videos_command,
    reveal_artifact_command,
    validate_character_registry_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ストーリーと素材から3秒単位のExcel絵コンテを作成します。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="素材を解析して3秒構成JSONを作成")
    create.add_argument("--input-dir", type=Path, default=ROOT / "input")
    create.add_argument("--output-root", type=Path, default=ROOT / "output" / "storyboard")
    create.add_argument("--story-model", default=None)
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

    return parser


def _dispatch(args: argparse.Namespace) -> str:
    if args.command == "create":
        result = create_command(
            input_dir=args.input_dir,
            output_root=args.output_root,
            story_model=args.story_model,
            character_registry_dir=args.character_registry_dir,
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
    elif args.command == "prepare-motions":
        result = prepare_motion_keyframes_command(
            args.registry_dir,
            args.overwrite,
        )
    elif args.command == "finalize-video":
        result = finalize_video_command(run_dir=args.run_dir)
    elif args.command == "build-video-workbook":
        result = build_video_workbook_command(run_dir=args.run_dir)
    elif args.command == "extract-corrections":
        result = extract_corrections_command(
            workbook_path=args.workbook,
            output_path=args.output,
        )
    elif args.command == "reveal-artifact":
        result = reveal_artifact_command(
            run_dir=args.run_dir,
            artifact=args.artifact,
            language=args.language,
            dry_run=args.dry_run,
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
