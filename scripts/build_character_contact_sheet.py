from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

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

    items: list[tuple[str, str, bool, Path]] = []
    for character in registry.lock_data()["characters"]:
        for reference in character["references"]:
            items.append(
                (
                    f"{character['id']}/{character['version']}",
                    reference["role"],
                    reference.get("use_for_generation", True),
                    registry.root / reference["path"],
                )
            )

    columns = 3
    image_width = 480
    image_height = 300
    label_height = 46
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new(
        "RGB",
        (columns * image_width, rows * (image_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    border_colors = {
        "identity": "#248f4b",
        "full_body": "#2374ab",
        "pose": "#b66b00",
        "motion_keyframe": "#7b4ab5",
        "anti_example": "#bd2c2c",
    }
    for index, (character, role, use_for_generation, path) in enumerate(items):
        x = (index % columns) * image_width
        y = (index // columns) * (image_height + label_height)
        with Image.open(path) as source:
            fitted = ImageOps.contain(
                source.convert("RGB"),
                (image_width - 16, image_height - 16),
                method=Image.Resampling.LANCZOS,
            )
        background = Image.new("RGB", (image_width, image_height), "#e8edf1")
        background.paste(
            fitted,
            ((image_width - fitted.width) // 2, (image_height - fitted.height) // 2),
        )
        canvas.paste(background, (x, y))
        draw.rectangle(
            (x + 2, y + 2, x + image_width - 3, y + image_height - 3),
            outline=(
                border_colors.get(role, "#555555")
                if use_for_generation
                else "#777777"
            ),
            width=6,
        )
        draw.text(
            (x + 10, y + image_height + 5),
            f"{character}  [{role}{'' if use_for_generation else ' / inactive'}]\n{path.name}",
            fill="black",
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
        default=ROOT / "characters" / "character_contact_sheet.png",
    )
    args = parser.parse_args()
    print(build(args.registry_dir.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
