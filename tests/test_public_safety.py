from pathlib import Path

from scripts.check_public_repo import is_local_env, validate_local_secret_ignores


def test_local_env_files_are_not_read_by_public_scan() -> None:
    assert is_local_env(Path(".env"))
    assert is_local_env(Path(".env.local"))
    assert not is_local_env(Path(".env.example"))


def test_required_env_ignore_rules_are_present() -> None:
    assert validate_local_secret_ignores() == []
