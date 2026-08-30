from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.artifacts import (  # noqa: E402
    is_directly_viewable,
    open_in_default_app,
    reveal_in_file_manager,
    spreadsheet_review_artifact,
)


def main() -> int:
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure:
                reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Open the artifact itself when possible, otherwise reveal its exact file."
    )
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--language", choices=("ja", "en"), default="ja")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.path.resolve()
    if target.suffix.lower() == ".xlsx":
        target = spreadsheet_review_artifact(target, args.language)
    if is_directly_viewable(target):
        if not target.is_file():
            message = (
                f"ACTION_REQUIRED: The review artifact does not exist: {target}"
                if args.language == "en"
                else f"ACTION_REQUIRED: 確認するファイルがありません: {target}"
            )
            print(message)
            return 1
        result = open_in_default_app(target, dry_run=args.dry_run)
        if not result.opened:
            print(
                f"ACTION_REQUIRED: Could not open the review artifact: {target}"
                if args.language == "en"
                else f"ACTION_REQUIRED: 確認するファイルを開けませんでした: {target}"
            )
            return 2
        kind = target.suffix.lower()
        if kind in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            ja_label, en_label = "確認する画像", "review image"
        elif kind in {".htm", ".html"}:
            ja_label, en_label = "確認画面", "review page"
        elif kind in {".mp4", ".mov", ".m4v", ".webm"}:
            ja_label, en_label = "確認する動画", "review video"
        else:
            ja_label, en_label = "確認するファイル", "review artifact"
        if args.dry_run:
            print(
                f"DRY RUN: Would open the {en_label} itself: {target}"
                if args.language == "en"
                else f"確認モード: {ja_label}そのものを開く予定です: {target}"
            )
            return 0
        print(
            f"Opened the {en_label} itself: {target.name}"
            if args.language == "en"
            else f"{ja_label}そのものを開きました: {target.name}"
        )
        return 0
    try:
        result = reveal_in_file_manager(target, dry_run=args.dry_run)
    except FileNotFoundError:
        if args.language == "en":
            print(f"ACTION_REQUIRED: The file does not exist: {target}")
        else:
            print(f"ACTION_REQUIRED: ファイルがありません: {target}")
        return 1

    if args.dry_run:
        if args.language == "en":
            print("DRY RUN: The folder was not opened.")
            print(f"Would select: {target}")
        else:
            print("確認モード: フォルダは実際には開いていません。")
            print(f"選択予定: {target}")
        return 0

    if args.language == "en":
        if result.opened:
            print(f"Folder opened: {target.parent}")
            if result.selected:
                print(f"File ready for review: {target.name}")
                print(
                    f"Double-click the displayed file {target.name}. "
                    "When it opens, reply: Opened."
                )
            else:
                print(f"File to find: {target.name}")
                print("Double-click that filename. When it opens, reply: Opened.")
            return 0
        print("ACTION_REQUIRED: This environment could not open the folder.")
        print(f"Folder: {target.parent}")
        print(f"File: {target.name}")
        print("Open that folder, then double-click the named file.")
        return 2

    if result.opened:
        print(f"フォルダを開きました: {target.parent}")
        if result.selected:
            print(f"確認するファイル: {target.name}")
            print(
                f"表示された「{target.name}」をダブルクリックしてください。"
                "開いたら「開いた」と返してください。"
            )
        else:
            print(f"探すファイル名: {target.name}")
            print(
                "同じ名前のファイルをダブルクリックしてください。"
                "開いたら「開いた」と返してください。"
            )
        return 0
    print("ACTION_REQUIRED: この環境からフォルダを開けませんでした。")
    print(f"フォルダ: {target.parent}")
    print(f"ファイル: {target.name}")
    print("そのフォルダを開き、同じ名前のファイルをダブルクリックしてください。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
