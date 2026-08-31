from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import current_storyboard_workbook, review_html_path
from .run_versions import (
    next_run_path,
    run_version_name,
    run_version_number,
    write_run_metadata,
)

REVISION_SCOPES = {"storyboard", "video", "audio"}


@dataclass(frozen=True)
class RunRevision:
    source_run: Path
    target_run: Path
    source_version: str
    target_version: str
    scope: str
    invalidated_shots: tuple[int, ...]
    record_path: Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision_output_root(source_run: Path) -> Path:
    if source_run.name.startswith("v"):
        return source_run.parent
    archive_record = source_run.parent / "archive_record.json"
    if archive_record.is_file():
        record = json.loads(archive_record.read_text(encoding="utf-8"))
        original = record.get("original_run_directory")
        if isinstance(original, str) and original:
            return Path(original).resolve().parent
    raise RuntimeError(
        "履歴から修正版を作るための元のoutput場所を判定できません: "
        f"{source_run}"
    )


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _normalize_storyboard_review(
    source_run: Path,
    target_run: Path,
    target_version: str,
) -> None:
    source_workbook = current_storyboard_workbook(source_run)
    if not source_workbook.is_file():
        raise FileNotFoundError(
            f"引き継ぐExcelコンテがありません: {source_workbook}"
        )
    target_review = target_run / "review"
    _remove_path(target_review)
    target_review.mkdir(parents=True)
    target_workbook = target_review / f"storyboard_{target_version}.xlsx"
    shutil.copy2(source_workbook, target_workbook)
    source_asset_dir = source_workbook.parent / f"{source_workbook.stem}_review_assets"
    target_asset_dir = target_workbook.parent / f"{target_workbook.stem}_review_assets"
    for language in ("ja", "en"):
        source_html = review_html_path(source_workbook, language)
        if source_html.is_file():
            target_html = review_html_path(target_workbook, language)
            html = source_html.read_text(encoding="utf-8").replace(
                source_asset_dir.name,
                target_asset_dir.name,
            )
            target_html.write_text(html, encoding="utf-8")
    if source_asset_dir.is_dir():
        shutil.copytree(source_asset_dir, target_asset_dir)


def _move_invalidated_shot_artifacts(
    target_run: Path,
    source_version: str,
    shot_numbers: set[int],
) -> list[str]:
    moved: list[str] = []
    rejected = target_run / "rejected" / f"from_{source_version}"
    for number in sorted(shot_numbers):
        clip = target_run / "video" / "clips" / f"shot_{number:03d}.mp4"
        raw = target_run / "video" / "raw" / f"shot_{number:03d}.mp4"
        metadata = target_run / "video" / "metadata" / f"shot_{number:03d}.json"
        continuity = (
            target_run
            / "video"
            / "continuity"
            / f"shot_{number:03d}_first_frame.png"
        )
        frame_dir = target_run / "frames" / f"shot_{number:03d}"
        for path, relative in (
            (clip, Path("video") / "clips" / clip.name),
            (raw, Path("video") / "raw" / raw.name),
            (metadata, Path("video") / "metadata" / metadata.name),
            (continuity, Path("video") / "continuity" / continuity.name),
            (frame_dir, Path("frames") / frame_dir.name),
        ):
            if not path.exists():
                continue
            destination = rejected / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            moved.append(relative.as_posix())
    return moved


def _available_clip_shots(run_dir: Path) -> set[int]:
    shots: set[int] = set()
    clips_dir = run_dir / "video" / "clips"
    if not clips_dir.is_dir():
        return shots
    for path in clips_dir.glob("shot_*.mp4"):
        suffix = path.stem.removeprefix("shot_")
        if len(suffix) == 3 and suffix.isdigit():
            shots.add(int(suffix))
    return shots


def create_run_revision(
    source_run: Path,
    *,
    scope: str,
    reason: str,
    affected_shots: tuple[int, ...] = (),
) -> RunRevision:
    """Clone an immutable reviewed run into the next whole vNNN revision."""
    source_run = source_run.resolve()
    if scope not in REVISION_SCOPES:
        raise ValueError(
            "scope must be one of: " + ", ".join(sorted(REVISION_SCOPES))
        )
    if not source_run.is_dir():
        raise FileNotFoundError(source_run)
    if not (source_run / "storyboard.json").is_file():
        raise FileNotFoundError(
            f"storyboard.jsonがないため修正版を作れません: {source_run}"
        )
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("reason must not be empty")
    if any(number < 1 for number in affected_shots):
        raise ValueError("affected shot numbers must be positive")

    source_version = run_version_name(source_run)
    output_root = _revision_output_root(source_run)
    output_root.mkdir(parents=True, exist_ok=True)
    target_run = next_run_path(
        output_root,
        minimum_version=run_version_number(source_run) + 1,
    )
    shutil.copytree(
        source_run,
        target_run,
        ignore=shutil.ignore_patterns("~$*", "*.tmp", "__pycache__"),
    )

    try:
        target_version = target_run.name
        write_run_metadata(target_run, source_version=source_version)
        _remove_path(target_run / "completion_state.json")
        _remove_path(target_run / "final")
        for path in target_run.glob("storyboard_r*.json"):
            path.unlink()
        for path in target_run.glob("corrections_storyboard_*.json"):
            path.unlink()
        _remove_path(target_run / "revision_log.jsonl")

        invalidated_shots: set[int] = set(affected_shots)
        invalidated_artifacts: list[str] = []
        if scope == "storyboard":
            _remove_path(target_run / "review")
            _remove_path(target_run / "video")
            _remove_path(target_run / "frames")
            _remove_path(target_run / "audio")
        else:
            _normalize_storyboard_review(source_run, target_run, target_version)
            if scope == "video":
                if not invalidated_shots:
                    invalidated_shots = _available_clip_shots(target_run)
                invalidated_artifacts = _move_invalidated_shot_artifacts(
                    target_run,
                    source_version,
                    invalidated_shots,
                )
                _remove_path(target_run / "audio")
            elif scope == "audio":
                _remove_path(target_run / "audio")

        source_storyboard = source_run / "storyboard.json"
        record = {
            "schema_version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "source_version": source_version,
            "target_version": target_version,
            "scope": scope,
            "reason": clean_reason,
            "affected_shots": sorted(invalidated_shots),
            "invalidated_artifacts": invalidated_artifacts,
            "source_storyboard_sha256": _sha256(source_storyboard),
            "source_run_preserved": True,
        }
        history_path = source_run / "revision_history.json"
        history: list[object] = []
        if history_path.is_file():
            loaded = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                history = loaded
        history.append(record)
        record_path = target_run / "revision_origin.json"
        record_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (target_run / "revision_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(target_run, ignore_errors=True)
        raise

    return RunRevision(
        source_run=source_run,
        target_run=target_run,
        source_version=source_version,
        target_version=target_version,
        scope=scope,
        invalidated_shots=tuple(sorted(invalidated_shots)),
        record_path=record_path,
    )
