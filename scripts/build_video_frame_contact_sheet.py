from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def build(run_dir: Path, destination: Path, shot_limit: int | None = None) -> Path:
    shot_dirs = sorted((run_dir / "frames").glob("shot_*"))
    if shot_limit is not None:
        shot_dirs = shot_dirs[:shot_limit]
    if not shot_dirs:
        raise FileNotFoundError(f"動画フレームがありません: {run_dir / 'frames'}")

    cell_width = 240
    frame_height = 135
    label_height = 22
    columns = 9
    canvas = Image.new(
        "RGB",
        (
            columns * cell_width,
            len(shot_dirs) * (frame_height + label_height),
        ),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    for row, shot_dir in enumerate(shot_dirs):
        frame_paths = sorted(shot_dir.glob("frame_*.jpg"))
        if len(frame_paths) != 9:
            raise RuntimeError(f"{shot_dir.name}: 9フレームではありません")
        for column, frame_path in enumerate(frame_paths):
            with Image.open(frame_path) as source:
                frame = ImageOps.fit(
                    source.convert("RGB"),
                    (cell_width, frame_height),
                    method=Image.Resampling.LANCZOS,
                )
            x = column * cell_width
            y = row * (frame_height + label_height)
            canvas.paste(frame, (x, y))
            draw.text(
                (x + 5, y + frame_height + 4),
                f"{shot_dir.name} F{column + 1:02d}",
                fill="black",
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() in {".jpg", ".jpeg"}:
        canvas.save(destination, format="JPEG", quality=90, optimize=True)
    else:
        canvas.save(destination, format="PNG", optimize=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shot-limit", type=int)
    args = parser.parse_args()
    print(
        build(
            args.run_dir.resolve(),
            args.output.resolve(),
            args.shot_limit,
        )
    )


if __name__ == "__main__":
    main()
