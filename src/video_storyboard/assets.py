from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageStat

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
SUPPORTED_ASSET_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_assets(source: Path, input_dir: Path) -> tuple[list[Path], list[Path]]:
    source = source.resolve()
    input_dir = input_dir.resolve()
    if source.is_file():
        candidates = [source]
    elif source.is_dir():
        candidates = sorted(
            path
            for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_ASSET_EXTENSIONS
        )
    else:
        raise FileNotFoundError(f"素材が見つかりません: {source}")
    if not candidates:
        raise RuntimeError("指定場所に対応する画像・動画・音声素材がありません。")

    input_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    unchanged: list[Path] = []
    reserved_names: dict[str, Path] = {}
    for candidate in candidates:
        folded = candidate.name.casefold()
        previous = reserved_names.get(folded)
        if previous is not None and previous != candidate:
            raise RuntimeError(
                "同じファイル名の素材が複数あります。名前を変えてから再試行してください: "
                f"{candidate.name}"
            )
        reserved_names[folded] = candidate
        destination = input_dir / candidate.name
        if destination.exists():
            if not destination.is_file() or _sha256(destination) != _sha256(candidate):
                raise FileExistsError(
                    "inputに同名の別ファイルがあります。上書きしていません: "
                    f"{destination.name}"
                )
            unchanged.append(destination)
            continue
        shutil.copy2(candidate, destination)
        copied.append(destination)
    return copied, unchanged


@dataclass
class AssetRecord:
    original_name: str
    original_path: str
    kind: str
    role: str
    notes: str
    prepared_path: str | None = None
    api_path: str | None = None
    character_pair_path: str | None = None
    cat_path: str | None = None
    dog_path: str | None = None


def read_story(input_dir: Path) -> tuple[Path, str]:
    preferred = (input_dir / "story.md", input_dir / "story.txt")
    for story_path in preferred:
        if story_path.is_file():
            return story_path, story_path.read_text(encoding="utf-8").strip()

    excluded_names = {"readme.md", "readme.txt"}
    candidates = [
        path
        for path in sorted(input_dir.glob("*.md"))
        + sorted(input_dir.glob("*.txt"))
        if path.name.casefold() not in excluded_names
        and not path.stem.casefold().startswith("sample_story")
    ]
    if not candidates:
        raise FileNotFoundError(
            f"{input_dir}に本番用のstory.mdまたはstory.txtがありません。"
        )
    if len(candidates) > 1:
        names = "、".join(path.name for path in candidates)
        raise ValueError(
            "本番用ストーリーを一つに決められません。"
            f"story.mdへまとめてください: {names}"
        )
    story_path = candidates[0]
    return story_path, story_path.read_text(encoding="utf-8").strip()


def _role_for_name(name: str, suffix: str) -> tuple[str, str]:
    stem = Path(name).stem
    if suffix in AUDIO_EXTENSIONS:
        return (
            "audio_reference",
            f"{stem}の声、効果音、音楽、または雰囲気の参照。",
        )
    if suffix in VIDEO_EXTENSIONS:
        return (
            "video_reference",
            f"{stem}の動き、外見、画角、雰囲気の参照。",
        )
    return "general_reference", f"{stem}の外見・色・形の一般参照素材。"


def _longest_bright_band(image: Image.Image) -> tuple[int, int]:
    sample = image.convert("L").resize((128, image.height))
    means = [ImageStat.Stat(sample.crop((0, y, 128, y + 1))).mean[0] for y in range(image.height)]
    mask = [value >= 18 for value in means]
    best_start = 0
    best_end = image.height
    current_start: int | None = None
    for index, enabled in enumerate(mask + [False]):
        if enabled and current_start is None:
            current_start = index
        elif not enabled and current_start is not None:
            if index - current_start > best_end - best_start:
                best_start, best_end = current_start, index
            current_start = None
    if best_end - best_start < image.height * 0.25:
        return 0, image.height
    return best_start, best_end


def _prepare_image(source: Path, destination: Path, crop_screenshot: bool) -> None:
    with Image.open(source) as image:
        image = image.convert("RGB")
        if crop_screenshot:
            top, bottom = _longest_bright_band(image)
            image = image.crop((0, top, image.width, bottom))
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="JPEG", quality=90, optimize=True)


def _extract_video_frame(source: Path, destination: Path, seconds: float = 5.0) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(seconds),
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        "scale=1280:-2",
        "-y",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("参照動画から静止画を抽出できませんでした。")


def prepare_assets(input_dir: Path, reference_dir: Path) -> list[AssetRecord]:
    records: list[AssetRecord] = []
    files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.suffix.lower()
        in SUPPORTED_ASSET_EXTENSIONS
    )
    for index, source in enumerate(files, start=1):
        suffix = source.suffix.lower()
        role, notes = _role_for_name(source.name, suffix)
        record = AssetRecord(
            original_name=source.name,
            original_path=str(source.resolve()),
            kind=(
                "video"
                if suffix in VIDEO_EXTENSIONS
                else "audio"
                if suffix in AUDIO_EXTENSIONS
                else "image"
            ),
            role=role,
            notes=notes,
        )
        if suffix in IMAGE_EXTENSIONS:
            prepared = reference_dir / f"ref_{index:02d}_{role}.jpg"
            _prepare_image(
                source,
                prepared,
                crop_screenshot=False,
            )
            record.prepared_path = str(prepared.resolve())
            record.api_path = str(prepared.resolve())
        elif suffix in VIDEO_EXTENSIONS:
            prepared = reference_dir / f"ref_{index:02d}_video_frame.jpg"
            _extract_video_frame(source, prepared)
            record.prepared_path = str(prepared.resolve())
            api_copy = reference_dir / f"ref_{index:02d}_source_video.mp4"
            shutil.copy2(source, api_copy)
            record.api_path = str(api_copy.resolve())
        else:
            api_copy = reference_dir / f"ref_{index:02d}_source_audio{suffix}"
            api_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, api_copy)
            record.api_path = str(api_copy.resolve())
        records.append(record)
    return records


def save_manifest(
    records: list[AssetRecord], story_path: Path, destination: Path
) -> None:
    run_dir = destination.parent.resolve()
    portable_records: list[dict[str, object]] = []
    for record in records:
        item = asdict(record)
        item["original_path"] = record.original_name
        for field in (
            "prepared_path",
            "api_path",
            "character_pair_path",
            "cat_path",
            "dog_path",
        ):
            value = item.get(field)
            if not value:
                continue
            resolved = Path(str(value)).resolve()
            try:
                item[field] = resolved.relative_to(run_dir).as_posix()
            except ValueError:
                item[field] = resolved.name
        portable_records.append(item)
    destination.write_text(
        json.dumps(
            {
                "story_file": story_path.name,
                "assets": portable_records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_manifest(path: Path) -> list[AssetRecord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records: list[AssetRecord] = []
    for raw_item in raw["assets"]:
        item = dict(raw_item)
        for field in (
            "prepared_path",
            "api_path",
            "character_pair_path",
            "cat_path",
            "dog_path",
        ):
            value = item.get(field)
            if value and not Path(str(value)).is_absolute():
                item[field] = str((path.parent / str(value)).resolve())
        records.append(AssetRecord(**item))
    return records
