from pathlib import Path

from video_storyboard.artifacts import (
    artifact_for_reveal,
    current_storyboard_workbook,
    current_video_review_workbook,
    detect_spreadsheet_viewers,
    is_directly_viewable,
    next_storyboard_workbook,
    next_video_review_workbook,
    open_in_default_app,
    reveal_in_file_manager,
    review_html_path,
    spreadsheet_review_artifact,
)


def test_images_html_and_video_open_as_the_artifact_itself(tmp_path: Path) -> None:
    for name in ("character.png", "character_review.ja.html", "final.mp4"):
        target = tmp_path / name
        target.touch()

        result = open_in_default_app(
            target,
            dry_run=True,
            system="Windows",
            environ={},
        )

        assert is_directly_viewable(target) is True
        assert result.opened is True
        assert result.command == ("startfile", str(target.resolve()))
        assert result.selected is False


def test_workbook_stays_a_named_manual_handoff(tmp_path: Path) -> None:
    workbook = tmp_path / "storyboard_v001.xlsx"
    workbook.touch()

    assert is_directly_viewable(workbook) is False


def test_storyboard_workbook_revisions_are_never_overwritten(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "v001"
    run_dir.mkdir()

    first = next_storyboard_workbook(run_dir)
    assert first == run_dir / "review" / "storyboard_v001.xlsx"
    first.parent.mkdir()
    first.touch()

    second = next_storyboard_workbook(run_dir)
    assert second.name == "storyboard_v001_r002.xlsx"
    second.touch()
    assert current_storyboard_workbook(run_dir) == second


def test_legacy_storyboard_is_found_and_next_build_is_revision_two(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "v003"
    run_dir.mkdir()
    legacy = run_dir / "storyboard_v003.xlsx"
    legacy.touch()

    assert current_storyboard_workbook(run_dir) == legacy
    assert next_storyboard_workbook(run_dir).name == "storyboard_v003_r002.xlsx"


def test_windows_spreadsheet_detection_finds_local_calc(tmp_path: Path) -> None:
    program_files = tmp_path / "Program Files"
    calc = program_files / "LibreOffice" / "program" / "scalc.exe"
    calc.parent.mkdir(parents=True)
    calc.touch()

    viewers = detect_spreadsheet_viewers(
        system="Windows",
        environ={"ProgramFiles": str(program_files)},
        which=lambda _name: None,
    )

    assert any(viewer.name == "LibreOffice Calc" for viewer in viewers)


def test_reveal_windows_selects_japanese_path_without_opening_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "確認用" / "絵コンテ.xlsx"
    target.parent.mkdir()
    target.touch()

    result = reveal_in_file_manager(
        target,
        dry_run=True,
        system="Windows",
        environ={},
    )

    assert result.opened is True
    assert result.command[0] == "explorer.exe"
    assert result.command[1].startswith("/select,")
    assert str(target.resolve()) in result.command[1]
    assert result.selected is True


def test_reveal_headless_linux_returns_safe_fallback(tmp_path: Path) -> None:
    target = tmp_path / "storyboard.xlsx"
    target.touch()

    result = reveal_in_file_manager(
        target,
        system="Linux",
        environ={},
    )

    assert result.opened is False
    assert result.command == ("xdg-open", str(tmp_path.resolve()))
    assert result.selected is False


def test_reveal_macos_uses_finder_reveal(tmp_path: Path) -> None:
    target = tmp_path / "storyboard.xlsx"
    target.touch()

    result = reveal_in_file_manager(
        target,
        dry_run=True,
        system="Darwin",
        environ={},
    )

    assert result.opened is True
    assert result.command == ("open", "-R", str(target.resolve()))
    assert result.selected is True


def test_reveal_linux_desktop_opens_containing_folder(tmp_path: Path) -> None:
    target = tmp_path / "final.mp4"
    target.touch()

    result = reveal_in_file_manager(
        target,
        dry_run=True,
        system="Linux",
        environ={"DISPLAY": ":0"},
    )

    assert result.opened is True
    assert result.command == ("xdg-open", str(tmp_path.resolve()))
    assert result.selected is False


def test_html_is_selected_when_no_spreadsheet_application_exists(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "v001"
    workbook = run_dir / "review" / "storyboard_v001.xlsx"
    workbook.parent.mkdir(parents=True)
    workbook.touch()
    html = review_html_path(workbook, "ja")
    html.touch()

    selected = artifact_for_reveal(
        run_dir,
        "storyboard",
        language="ja",
        spreadsheet_available=False,
    )

    assert selected == html
    assert spreadsheet_review_artifact(
        workbook,
        "ja",
        spreadsheet_available=False,
    ) == html


def test_final_artifacts_and_video_review_use_the_same_handoff(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "v004"
    final_dir = run_dir / "final"
    final_dir.mkdir(parents=True)
    video = final_dir / "story_video_v004.mp4"
    record = final_dir / "AIモデル使用記録.md"
    video.touch()
    record.touch()

    first_review = next_video_review_workbook(run_dir)
    first_review.touch()
    second_review = next_video_review_workbook(run_dir)

    assert second_review.name == "storyboard_v004_video_r002.xlsx"
    assert current_video_review_workbook(run_dir) == first_review
    assert artifact_for_reveal(run_dir, "final-video") == video
    assert artifact_for_reveal(run_dir, "ai-record", language="ja") == record
