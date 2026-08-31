from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

RUN_VERSION_PATTERN = re.compile(r"v(\d{3})")


def _validated_version(value: object) -> str | None:
    if isinstance(value, str) and RUN_VERSION_PATTERN.fullmatch(value):
        return value
    return None


def run_version_name(run_dir: Path) -> str:
    """Return the vNNN identity, including for a run moved into history."""
    run_dir = run_dir.resolve()
    direct = _validated_version(run_dir.name)
    if direct:
        return direct

    metadata_path = run_dir / "run_metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        version = _validated_version(metadata.get("version"))
        if not version:
            raise RuntimeError(
                f"run_metadata.jsonのversionが不正です: {metadata_path}"
            )
        return version

    candidates: set[str] = set()
    patterns = (
        (run_dir / "review", "storyboard_v*.xlsx"),
        (run_dir / "final", "storyboard_v*_video*.xlsx"),
        (run_dir / "final", "story_video_v*.mp4"),
        (run_dir, "storyboard_v*.xlsx"),
    )
    for directory, pattern in patterns:
        if not directory.is_dir():
            continue
        for path in directory.glob(pattern):
            match = re.search(r"(?:storyboard_|story_video_)(v\d{3})", path.name)
            if match:
                candidates.add(match.group(1))
    if len(candidates) == 1:
        return candidates.pop()
    if not candidates:
        raise RuntimeError(
            f"制作ランの版を判定できません。vNNNフォルダーではありません: {run_dir}"
        )
    raise RuntimeError(
        "制作ランに複数の版名が混在しています: " + ", ".join(sorted(candidates))
    )


def run_version_number(run_dir: Path) -> int:
    return int(run_version_name(run_dir)[1:])


def next_run_path(output_root: Path, *, minimum_version: int = 1) -> Path:
    output_root = output_root.resolve()
    versions: list[int] = []
    if output_root.is_dir():
        for path in output_root.iterdir():
            match = RUN_VERSION_PATTERN.fullmatch(path.name)
            if path.is_dir() and match:
                versions.append(int(match.group(1)))
    version = max(max(versions, default=0) + 1, minimum_version)
    return output_root / f"v{version:03d}"


def allocate_run_dir(output_root: Path, *, minimum_version: int = 1) -> Path:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = next_run_path(output_root, minimum_version=minimum_version)
    run_dir.mkdir(exist_ok=False)
    write_run_metadata(run_dir)
    return run_dir


def write_run_metadata(
    run_dir: Path,
    *,
    source_version: str | None = None,
) -> Path:
    run_dir = run_dir.resolve()
    version = _validated_version(run_dir.name)
    if not version:
        raise ValueError(f"run directory must be named vNNN: {run_dir}")
    destination = run_dir / "run_metadata.json"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if source_version:
        validated_source = _validated_version(source_version)
        if not validated_source:
            raise ValueError(f"source_version must be vNNN: {source_version}")
        payload["source_version"] = validated_source
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
