from pathlib import Path

import pytest

from video_storyboard import updates


@pytest.mark.parametrize(
    ("relation", "expected_ja", "expected_en"),
    (
        ("same", "現在版と一致", "matches the GitHub branch"),
        ("local_behind", "新しい更新版", "newer revision is available"),
        ("local_ahead", "更新候補ではありません", "not an available update"),
        ("diverged", "履歴が分岐", "have diverged"),
    ),
)
def test_update_message_distinguishes_revision_direction(
    relation: str, expected_ja: str, expected_en: str
) -> None:
    status = updates.UpdateStatus(
        branch="main",
        local_commit="local",
        remote_commit="remote",
        remote_url="https://example.invalid/repo.git",
        dirty_files=0,
        relation=relation,
    )

    assert expected_ja in updates.format_update_status(status, "ja")
    assert expected_en in updates.format_update_status(status, "en")


def test_check_for_updates_reports_local_ahead(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local_commit = "a" * 40
    remote_commit = "b" * 40

    def fake_git(_root: Path, *args: str) -> str:
        commands = {
            ("symbolic-ref", "--short", "HEAD"): "main",
            ("rev-parse", "HEAD"): local_commit,
            ("remote", "get-url", "origin"): "https://example.invalid/repo.git",
            ("ls-remote", "--heads", "origin", "refs/heads/main"): (
                f"{remote_commit}\trefs/heads/main"
            ),
            ("status", "--porcelain"): "",
        }
        return commands[args]

    def fake_returncode(_root: Path, *args: str) -> int:
        if args[:2] == ("cat-file", "-e"):
            return 0
        if args == (
            "merge-base",
            "--is-ancestor",
            remote_commit,
            local_commit,
        ):
            return 0
        return 1

    monkeypatch.setattr(updates, "_git", fake_git)
    monkeypatch.setattr(updates, "_git_returncode", fake_returncode)

    status = updates.check_for_updates(tmp_path)

    assert status.relation == "local_ahead"
    assert not status.update_available

