from __future__ import annotations

import json
import shutil
from pathlib import Path

from video_storyboard.artifacts import current_storyboard_workbook
from video_storyboard.revisions import create_run_revision
from video_storyboard.run_versions import write_run_metadata


def _source_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "output" / "project" / "v001"
    (run_dir / "review").mkdir(parents=True)
    (run_dir / "video" / "clips").mkdir(parents=True)
    (run_dir / "video" / "raw").mkdir(parents=True)
    (run_dir / "video" / "metadata").mkdir(parents=True)
    (run_dir / "video" / "continuity").mkdir(parents=True)
    (run_dir / "frames" / "shot_001").mkdir(parents=True)
    (run_dir / "frames" / "shot_002").mkdir(parents=True)
    (run_dir / "final").mkdir(parents=True)
    (run_dir / "audio").mkdir(parents=True)
    (run_dir / "storyboard.json").write_text(
        json.dumps({"title": "test"}), encoding="utf-8"
    )
    (run_dir / "manifest.json").write_text(
        json.dumps({"assets": []}), encoding="utf-8"
    )
    (run_dir / "review" / "storyboard_v001.xlsx").write_bytes(b"approved")
    (run_dir / "review" / "storyboard_v001_review.ja.html").write_text(
        '<img src="storyboard_v001_review_assets/shot_001_main.jpg">',
        encoding="utf-8",
    )
    source_assets = run_dir / "review" / "storyboard_v001_review_assets"
    source_assets.mkdir()
    (source_assets / "shot_001_main.jpg").write_bytes(b"image")
    for number in (1, 2):
        (run_dir / "video" / "clips" / f"shot_{number:03d}.mp4").write_bytes(
            f"clip-{number}".encode()
        )
        (run_dir / "video" / "raw" / f"shot_{number:03d}.mp4").write_bytes(
            f"raw-{number}".encode()
        )
        (run_dir / "video" / "metadata" / f"shot_{number:03d}.json").write_text(
            "{}", encoding="utf-8"
        )
        (
            run_dir
            / "video"
            / "continuity"
            / f"shot_{number:03d}_first_frame.png"
        ).write_bytes(f"continuity-{number}".encode())
        (run_dir / "frames" / f"shot_{number:03d}" / "frame_01.jpg").write_bytes(
            f"frame-{number}".encode()
        )
    (run_dir / "audio" / "mix.json").write_text("{}", encoding="utf-8")
    (run_dir / "final" / "story_video_v001.mp4").write_bytes(b"final")
    (run_dir / "completion_state.json").write_text("{}", encoding="utf-8")
    write_run_metadata(run_dir)
    return run_dir


def test_video_revision_creates_next_run_and_preserves_source(tmp_path: Path) -> None:
    source = _source_run(tmp_path)

    revision = create_run_revision(
        source,
        scope="video",
        reason="S002の動きを修正",
        affected_shots=(2,),
    )

    target = revision.target_run
    assert target.name == "v002"
    assert (source / "final" / "story_video_v001.mp4").is_file()
    assert (source / "video" / "clips" / "shot_002.mp4").is_file()
    assert current_storyboard_workbook(target).name == "storyboard_v002.xlsx"
    target_html = target / "review" / "storyboard_v002_review.ja.html"
    assert "storyboard_v002_review_assets" in target_html.read_text(
        encoding="utf-8"
    )
    assert (
        target
        / "review"
        / "storyboard_v002_review_assets"
        / "shot_001_main.jpg"
    ).is_file()
    assert (target / "video" / "clips" / "shot_001.mp4").is_file()
    assert not (target / "video" / "clips" / "shot_002.mp4").exists()
    assert (
        target
        / "rejected"
        / "from_v001"
        / "video"
        / "clips"
        / "shot_002.mp4"
    ).is_file()
    assert (
        target / "rejected" / "from_v001" / "video" / "raw" / "shot_002.mp4"
    ).is_file()
    assert (
        target
        / "rejected"
        / "from_v001"
        / "video"
        / "metadata"
        / "shot_002.json"
    ).is_file()
    assert (
        target
        / "rejected"
        / "from_v001"
        / "video"
        / "continuity"
        / "shot_002_first_frame.png"
    ).is_file()
    assert not (target / "final").exists()
    assert not (target / "audio").exists()
    assert not (target / "completion_state.json").exists()
    record = json.loads((target / "revision_origin.json").read_text(encoding="utf-8"))
    assert record["source_version"] == "v001"
    assert record["target_version"] == "v002"
    assert record["affected_shots"] == [2]


def test_audio_revision_can_resume_from_archived_run(tmp_path: Path) -> None:
    source = _source_run(tmp_path)
    original = source.resolve()
    archive = tmp_path / "history" / "001_test"
    archive.mkdir(parents=True)
    archived_run = Path(shutil.move(str(source), str(archive / "run")))
    (archive / "archive_record.json").write_text(
        json.dumps({"original_run_directory": str(original)}),
        encoding="utf-8",
    )

    revision = create_run_revision(
        archived_run,
        scope="audio",
        reason="鳴き声をかわいくする",
    )

    target = revision.target_run
    assert target == original.parent / "v002"
    assert archived_run.is_dir()
    assert current_storyboard_workbook(archived_run).name == "storyboard_v001.xlsx"
    assert current_storyboard_workbook(target).name == "storyboard_v002.xlsx"
    assert (target / "video" / "clips" / "shot_001.mp4").is_file()
    assert not (target / "audio").exists()
    assert not (target / "final").exists()


def test_revision_never_reuses_an_existing_version(tmp_path: Path) -> None:
    source = _source_run(tmp_path)
    existing = source.parent / "v002"
    existing.mkdir()

    revision = create_run_revision(
        source,
        scope="audio",
        reason="音声を調整",
    )

    assert revision.target_run.name == "v003"
    assert existing.is_dir()
