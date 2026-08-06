from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.character_registry import CharacterRegistry  # noqa: E402


def build(registry_dir: Path, destination: Path) -> Path:
    registry = CharacterRegistry.load(registry_dir)
    issues = registry.validate()
    if issues:
        raise RuntimeError("\n".join(issues))

    rows: list[tuple[str, str, list[tuple[Path, float]]]] = []
    for record in registry.records:
        motions = []
        if record.design_video:
            motions.append((record.design_video, "常時参照"))
        motions.extend((motion, "固有動作") for motion in record.motions)
        for motion, mode in motions:
            frames = [
                (registry.asset_path(record, path), seconds)
                for path, seconds in zip(
                    motion.keyframes,
                    motion.keyframe_times_seconds,
                    strict=True,
                )
            ]
            rows.append(
                (
                    f"{record.name_ja}  {record.id}/{record.version}",
                    f"{motion.name_ja}  [{motion.id} / {mode}]",
                    frames,
                )
            )

    columns = 3
    cell_width = 430
    image_height = 300
    heading_height = 52
    cell_label_height = 24
    row_height = heading_height + image_height + cell_label_height
    canvas = Image.new(
        "RGB",
        (columns * cell_width, max(1, len(rows)) * row_height),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/meiryo.ttc")
    heading_font = (
        ImageFont.truetype(str(font_path), 16)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    label_font = (
        ImageFont.truetype(str(font_path), 12)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    for row_index, (character, motion, frames) in enumerate(rows):
        top = row_index * row_height
        draw.rectangle(
            (0, top, columns * cell_width, top + heading_height - 1),
            fill="#283847",
        )
        draw.text((12, top + 7), character, fill="white", font=heading_font)
        draw.text((330, top + 7), motion, fill="#d9e8f2", font=heading_font)
        for column, (path, seconds) in enumerate(frames):
            x = column * cell_width
            y = top + heading_height
            with Image.open(path) as source:
                fitted = ImageOps.contain(
                    source.convert("RGB"),
                    (cell_width - 16, image_height - 16),
                    method=Image.Resampling.LANCZOS,
                )
            background = Image.new("RGB", (cell_width, image_height), "#dfe6ea")
            background.paste(
                fitted,
                ((cell_width - fitted.width) // 2, (image_height - fitted.height) // 2),
            )
            canvas.paste(background, (x, y))
            draw.rectangle(
                (x + 2, y + 2, x + cell_width - 3, y + image_height - 3),
                outline="#7b4ab5",
                width=5,
            )
            draw.text(
                (x + 10, y + image_height + 4),
                f"{seconds:.2f}s  {path.name}",
                fill="black",
                font=label_font,
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=ROOT / "characters",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "characters" / "motion_contact_sheet.png",
    )
    args = parser.parse_args()
    print(build(args.registry_dir.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
