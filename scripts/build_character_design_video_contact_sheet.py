from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def build(characters_dir: Path, destination: Path) -> Path:
    rows: list[tuple[str, str, list[Path]]] = []
    for metadata_path in characters_dir.glob(
        "*/v*/design_videos/v002/*_design.json"
    ):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        motion_id = metadata["motion_id"]
        frame_dir = metadata_path.parent / f"{motion_id}_frames"
        frames = sorted(frame_dir.glob("frame_*.jpg"))
        if len(frames) != 9:
            raise RuntimeError(
                f"Expected 9 frames for {metadata_path}, found {len(frames)}"
            )
        rows.append(
            (
                f"{metadata['character_name']}  {metadata['character_id']}/"
                f"{metadata['profile_version']}",
                f"{metadata.get('action_ja', motion_id)}  [{motion_id}]",
                frames,
            )
        )
    rows.sort(key=lambda row: str(row[2][0]))

    columns = 9
    cell_width = 240
    image_height = 135
    heading_height = 48
    label_height = 20
    row_height = heading_height + image_height + label_height
    canvas = Image.new(
        "RGB",
        (columns * cell_width, max(1, len(rows)) * row_height),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/meiryo.ttc")
    heading_font = (
        ImageFont.truetype(str(font_path), 15)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    label_font = (
        ImageFont.truetype(str(font_path), 11)
        if font_path.is_file()
        else ImageFont.load_default()
    )
    for row_index, (character, motion, frames) in enumerate(rows):
        top = row_index * row_height
        draw.rectangle(
            (0, top, columns * cell_width, top + heading_height - 1),
            fill="#283847",
        )
        draw.text((12, top + 5), character, fill="white", font=heading_font)
        draw.text((360, top + 5), motion, fill="#d9e8f2", font=heading_font)
        for column, frame in enumerate(frames):
            x = column * cell_width
            y = top + heading_height
            with Image.open(frame) as source:
                fitted = ImageOps.fit(
                    source.convert("RGB"),
                    (cell_width, image_height),
                    method=Image.Resampling.LANCZOS,
                )
            canvas.paste(fitted, (x, y))
            draw.rectangle(
                (x + 1, y + 1, x + cell_width - 2, y + image_height - 2),
                outline="#4b8fbd",
                width=3,
            )
            draw.text(
                (x + 8, y + image_height + 2),
                f"{(column + 1) / 3:.3f}s",
                fill="black",
                font=label_font,
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", optimize=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--characters-dir",
        type=Path,
        default=ROOT / "characters",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "characters" / "design_video_contact_sheet_v002.png",
    )
    args = parser.parse_args()
    print(build(args.characters_dir.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
