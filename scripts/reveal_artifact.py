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
        description="Open an artifact's folder and select the artifact."
    )
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--language", choices=("ja", "en"), default="ja")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.path.resolve()
    if target.suffix.lower() == ".xlsx":
        target = spreadsheet_review_artifact(target, args.language)
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
                print(f"Selected file: {target.name}")
                print(
                    "Double-click the selected file. "
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
            print(f"青く選択されたファイル: {target.name}")
            print(
                "そのファイルをダブルクリックしてください。"
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
