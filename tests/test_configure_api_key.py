from __future__ import annotations

from pathlib import Path

from scripts.configure_api_key import (
    read_configured_key,
    update_env_text,
    validate_api_key,
    write_api_key,
)


def test_update_env_text_preserves_other_settings_and_removes_duplicates() -> None:
    original = (
        "# local settings\nOTHER=value\nGEMINI_API_KEY=old\nGEMINI_API_KEY=duplicate\n"
    )
    updated = update_env_text(original, "example_key_12345678901234567890")

    assert "# local settings" in updated
    assert "OTHER=value" in updated
    assert updated.count("GEMINI_API_KEY=") == 1
    assert "old" not in updated
    assert "duplicate" not in updated


def test_write_api_key_creates_local_env_without_echoing(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    key = "example_key_12345678901234567890"

    write_api_key(env_path, key)

    assert read_configured_key(env_path, environ={}) is True
    assert env_path.read_text(encoding="utf-8").strip() == f"GEMINI_API_KEY={key}"


def test_validate_api_key_rejects_empty_short_or_whitespace() -> None:
    assert validate_api_key("") is not None
    assert validate_api_key("too-short") is not None
    assert validate_api_key("example key with spaces 123456789") is not None
    assert validate_api_key("example_key_12345678901234567890") is None
