from __future__ import annotations

from pathlib import Path

import pytest

from run_storyboard import build_parser
from video_storyboard import pipeline


def test_create_requires_an_explicit_user_selected_aspect_ratio() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args(["create"])

    assert error.value.code == 2


@pytest.mark.parametrize("aspect_ratio", ["9:16", "16:9"])
def test_create_accepts_both_supported_aspect_ratios(aspect_ratio: str) -> None:
    args = build_parser().parse_args(["create", "--aspect-ratio", aspect_ratio])

    assert args.aspect_ratio == aspect_ratio


def test_create_command_rejects_a_missing_aspect_ratio(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="--aspect-ratio"):
        pipeline.create_command(tmp_path, tmp_path / "output")


def test_prepare_tutorial_sample_story_write_is_explicit() -> None:
    args = build_parser().parse_args(
        [
            "prepare-tutorial",
            "--youtube-url",
            "https://youtu.be/6xOhd6PD3V8",
            "--language",
            "ja",
            "--write-sample-story",
        ]
    )

    assert args.write_sample_story is True
    assert args.input_dir.name == "input"


def test_completion_status_accepts_language_for_consistent_agent_usage() -> None:
    args = build_parser().parse_args(["completion-status", "--language", "ja"])

    assert args.language == "ja"
    assert args.output_root.name == "output"


def test_import_input_accepts_a_user_supplied_source_folder() -> None:
    args = build_parser().parse_args(
        ["import-input", "--source", "C:/materials"]
    )

    assert str(args.source).replace("\\", "/") == "C:/materials"


def test_revise_run_accepts_video_scope_and_repeatable_shots() -> None:
    args = build_parser().parse_args(
        [
            "revise-run",
            "--run-dir",
            "output/example/v001",
            "--scope",
            "video",
            "--reason",
            "S001を修正",
            "--shot",
            "1",
            "--shot",
            "3",
        ]
    )

    assert args.scope == "video"
    assert args.shot == [1, 3]


def test_apply_corrections_accepts_chat_corrections_file() -> None:
    args = build_parser().parse_args(
        [
            "apply-corrections",
            "--run-dir",
            "output/example/v001",
            "--corrections-file",
            "corrections.json",
        ]
    )

    assert args.corrections_file == Path("corrections.json")
