from pathlib import Path

import pytest

from video_storyboard.assets import prepare_assets, read_story


def test_read_story_prefers_production_story_over_sample(tmp_path: Path) -> None:
    (tmp_path / "sample_story.md").write_text("sample", encoding="utf-8")
    (tmp_path / "story.md").write_text("production", encoding="utf-8")

    path, content = read_story(tmp_path)

    assert path.name == "story.md"
    assert content == "production"


def test_read_story_rejects_sample_without_production_story(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("instructions", encoding="utf-8")
    (tmp_path / "sample_story.md").write_text("sample", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="story.mdまたはstory.txt"):
        read_story(tmp_path)


def test_read_story_rejects_ambiguous_custom_story_files(tmp_path: Path) -> None:
    (tmp_path / "idea.md").write_text("idea", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")

    with pytest.raises(ValueError, match="一つに決められません"):
        read_story(tmp_path)


def test_audio_reference_is_copied_into_the_private_run(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    reference_dir = tmp_path / "run" / "references"
    input_dir.mkdir()
    (input_dir / "music.mp3").write_bytes(b"rights-cleared test audio")

    records = prepare_assets(input_dir, reference_dir)

    assert len(records) == 1
    assert records[0].kind == "audio"
    assert records[0].role == "audio_reference"
    assert Path(records[0].api_path).read_bytes() == b"rights-cleared test audio"
