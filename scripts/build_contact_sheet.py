from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def build(run_dir: Path, destination: Path | None = None) -> Path:
    image_paths = sorted((run_dir / "images").glob("shot_*.png"))
    if not image_paths:
        raise FileNotFoundError(f"ショット画像がありません: {run_dir / 'images'}")

    columns = 3
    cell_width = 480
    frame_height = 270
    label_height = 28
    rows = (len(image_paths) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * cell_width, rows * (frame_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    for index, path in enumerate(image_paths):
        with Image.open(path) as source:
            frame = ImageOps.fit(
                source.convert("RGB"),
                (cell_width, frame_height),
                method=Image.Resampling.LANCZOS,
            )
        x = (index % columns) * cell_width
        y = (index // columns) * (frame_height + label_height)
        canvas.paste(frame, (x, y))
        draw.text((x + 8, y + frame_height + 6), path.stem, fill="black")

    output = destination or run_dir / "contact_sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build(args.run_dir.resolve(), args.output))


if __name__ == "__main__":
    main()
