from pathlib import Path

from scripts.check_public_repo import (
    is_local_env,
    text_files,
    validate_local_secret_ignores,
)


def test_local_env_files_are_not_read_by_public_scan() -> None:
    assert is_local_env(Path(".env"))
    assert is_local_env(Path(".env.local"))
    assert not is_local_env(Path(".env.example"))


def test_required_env_ignore_rules_are_present() -> None:
    assert validate_local_secret_ignores() == []


def test_git_ignored_operator_notes_are_not_scanned_as_publishable_files() -> None:
    assert all(path.name != "運営者用.md" for path in text_files())
