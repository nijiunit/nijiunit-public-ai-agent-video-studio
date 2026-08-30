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
    prepare_review_copy,
    reveal_handoff_message,
    reveal_in_file_manager,
    review_copy_path,
    spreadsheet_review_artifact,
)


def main() -> int:
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure:
                reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Open an artifact's folder and reveal its exact filename."
    )
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--language", choices=("ja", "en"), default="ja")
    parser.add_argument(
        "--display-name",
        help="Short exact filename shown to the beginner; creates a safe review copy.",
    )
    parser.add_argument(
        "--review-dir",
        type=Path,
        help="Optional folder for the short review copy.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.path.resolve()
    if target.suffix.lower() == ".xlsx":
        target = spreadsheet_review_artifact(target, args.language)
    if args.display_name:
        try:
            if args.dry_run:
                target = review_copy_path(target, args.display_name, args.review_dir)
            else:
                target = prepare_review_copy(target, args.display_name, args.review_dir)
        except (FileNotFoundError, ValueError) as error:
            print(f"ACTION_REQUIRED: {error}")
            return 1
    if args.dry_run:
        print(reveal_handoff_message(target, None, language=args.language, dry_run=True))
        return 0
    try:
        result = reveal_in_file_manager(target)
    except FileNotFoundError:
        if args.language == "en":
            print(f"ACTION_REQUIRED: The file does not exist: {target}")
        else:
            print(f"ACTION_REQUIRED: ファイルがありません: {target}")
        return 1

    print(reveal_handoff_message(target, result, language=args.language))
    return 0 if result.opened else 2


if __name__ == "__main__":
    raise SystemExit(main())
