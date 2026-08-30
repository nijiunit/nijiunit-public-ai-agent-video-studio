from __future__ import annotations

import json
from pathlib import Path

import pytest

from video_storyboard.history import (
    archive_production,
    completion_status,
    is_completion_confirmation,
    mark_completion_review_pending,
)


@pytest.mark.parametrize(
    "value",
    ["この内容で完成です", "これでいいです", "問題ありません", "OKです"],
)
def test_completion_accepts_natural_equivalents(value: str) -> None:
    assert is_completion_confirmation(value)


@pytest.mark.parametrize("value", ["まだ修正したい", "ここを直して", "問題があります"])
def test_completion_rejects_correction_requests(value: str) -> None:
    assert not is_completion_confirmation(value)


def test_archive_moves_run_and_keeps_it_editable(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "storyboard" / "v001"
    final_dir = run_dir / "final"
    final_dir.mkdir(parents=True)
    (run_dir / "storyboard.json").write_text(
        json.dumps({"title": "小さな作品"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (final_dir / "story_video_v001.mp4").write_bytes(b"video")
    workbook = final_dir / "storyboard_v001_video.xlsx"
    workbook.write_bytes(b"workbook")
    mark_completion_review_pending(run_dir, workbook)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "story.md").write_text("story", encoding="utf-8")
    history_root = tmp_path / "history"

    archive = archive_production(
        run_dir,
        input_dir,
        history_root,
        "これでいいです",
    )

    assert not run_dir.exists()
    assert (archive / "run" / "final" / "story_video_v001.mp4").is_file()
    assert (archive / "input" / "story.md").is_file()
    assert (archive / "manifest.sha256.json").is_file()
    editable = archive / "run" / "notes_after_archive.txt"
    editable.write_text("修正再開可能", encoding="utf-8")
    assert editable.is_file()
    assert completion_status(tmp_path / "output" / "storyboard", history_root)[
        "history"
    ] == [str(archive.resolve())]
