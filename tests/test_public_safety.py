from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.check_public_repo import (
    is_local_env,
    publishable_files,
    scan_publishable_files,
    validate_local_secret_ignores,
    validate_no_tracked_local_env,
)


def init_git_repository(path: Path) -> None:
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def test_local_env_files_are_recognized() -> None:
    assert is_local_env(Path(".env"))
    assert is_local_env(Path(".env.local"))
    assert not is_local_env(Path(".env.example"))


def test_required_local_document_and_env_ignore_rules_are_present() -> None:
    assert validate_local_secret_ignores() == []


def test_untracked_publishable_file_is_scanned(tmp_path: Path) -> None:
    init_git_repository(tmp_path)
    test_key = "AIza" + "A" * 35
    (tmp_path / "new-page.html").write_text(test_key, encoding="utf-8")

    assert any(
        issue == "new-page.html: possible Google API key"
        for issue in scan_publishable_files(tmp_path)
    )


def test_ignored_secret_file_is_not_a_publishable_candidate(tmp_path: Path) -> None:
    init_git_repository(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env").write_text("AIza" + "A" * 35, encoding="utf-8")

    assert all(path.name != ".env" for path in publishable_files(tmp_path))


def test_tracked_local_env_fails_even_when_ignored(tmp_path: Path) -> None:
    init_git_repository(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SAFE_TEST_VALUE=1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "--force", ".env"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    assert validate_no_tracked_local_env(tmp_path) == [
        ".env: local environment file must not be tracked"
    ]


def test_documented_user_placeholder_is_not_personal_information(tmp_path: Path) -> None:
    init_git_repository(tmp_path)
    safe_path = "C:" + "\\Users\\[user]\\Documents\\Codex"
    (tmp_path / "guide.md").write_text(safe_path, encoding="utf-8")

    assert scan_publishable_files(tmp_path) == []
