from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE_PAIRS = (
    ("README.md", "README.ja.md"),
    ("docs/getting-started.md", "docs/getting-started.ja.md"),
    ("docs/python-setup.md", "docs/python-setup.ja.md"),
    ("docs/google-api-setup.md", "docs/google-api-setup.ja.md"),
    ("docs/agent-guide.md", "docs/agent-guide.ja.md"),
    ("docs/releasing.md", "docs/releasing.ja.md"),
    ("WORKFLOW.md", "作業手順.md"),
)


def test_required_language_pairs_exist_and_link_to_each_other() -> None:
    for english_relative, japanese_relative in LANGUAGE_PAIRS:
        english = ROOT / english_relative
        japanese = ROOT / japanese_relative

        assert english.is_file(), f"missing English guide: {english_relative}"
        assert japanese.is_file(), f"missing Japanese guide: {japanese_relative}"

        english_text = english.read_text(encoding="utf-8")
        japanese_text = japanese.read_text(encoding="utf-8")
        assert japanese.name in english_text, (
            f"{english_relative} does not link to {japanese_relative}"
        )
        assert english.name in japanese_text, (
            f"{japanese_relative} does not link to {english_relative}"
        )


def test_agent_router_preserves_the_selected_language() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "docs/agent-guide.md" in instructions
    assert "docs/agent-guide.ja.md" in instructions
    assert "Preserve the user's language" in instructions
    assert "日本語とEnglishのどちらで進めますか？" in instructions
