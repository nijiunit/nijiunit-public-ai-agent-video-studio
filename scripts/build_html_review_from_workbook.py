from __future__ import annotations

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import load_workbook
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.review_html import create_review_html  # noqa: E402
from video_storyboard.schema import Storyboard  # noqa: E402


def extract_main_images(workbook_path: Path, image_dir: Path) -> int:
    """Extract each shot's embedded main image for legacy HTML conversion."""
    workbook = load_workbook(workbook_path, data_only=False)
    extracted = 0
    image_dir.mkdir(parents=True, exist_ok=True)
    for worksheet in workbook.worksheets:
        if not worksheet.title.startswith("S"):
            continue
        try:
            shot_number = int(worksheet.title[1:4])
        except ValueError:
            continue
        if not worksheet._images:
            raise RuntimeError(
                f"No embedded main image was found in {worksheet.title}"
            )
        with Image.open(BytesIO(worksheet._images[0]._data())) as image:
            image.convert("RGB").save(
                image_dir / f"shot_{shot_number:03d}.png"
            )
        extracted += 1
    return extracted


def main() -> int:
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure:
                reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description=(
            "Build offline Japanese and English storyboard review pages from "
            "a legacy workbook. No network or generation API is used."
        )
    )
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--language",
        choices=("ja", "en", "all"),
        default="all",
    )
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    workbook_path = args.workbook.resolve()
    output_dir = (
        args.output_dir.resolve() if args.output_dir else workbook_path.parent
    )
    storyboard = Storyboard.model_validate_json(
        storyboard_path.read_text(encoding="utf-8")
    )
    languages = ("ja", "en") if args.language == "all" else (args.language,)

    with TemporaryDirectory(prefix="nijiunit-review-") as temporary:
        run_dir = Path(temporary)
        count = extract_main_images(workbook_path, run_dir / "images")
        if count != len(storyboard.shots):
            raise RuntimeError(
                f"Workbook images={count}, storyboard shots={len(storyboard.shots)}"
            )
        for language in languages:
            destination = output_dir / (
                f"{workbook_path.stem}_review.{language}.html"
            )
            create_review_html(
                storyboard,
                run_dir,
                destination,
                language=language,
            )
            print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
