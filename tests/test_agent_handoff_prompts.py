from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.sync_agent_handoff_prompts import ROOT, rendered_prompts


def test_only_verified_routes_are_publishable() -> None:
    assert set(rendered_prompts()) == {("ja", "chatgpt-codex")}


def test_six_agent_language_routes_are_independent() -> None:
    prompts = rendered_prompts(include_unverified=True)
    assert set(prompts) == {
        ("ja", "chatgpt-codex"),
        ("ja", "claude-code"),
        ("ja", "gemini-cli"),
        ("en", "chatgpt-codex"),
        ("en", "claude-code"),
        ("en", "gemini-cli"),
    }
    assert ROOT.joinpath("config/agent-handoff/ja/codex-handoff.md").read_text(
        encoding="utf-8"
    ).strip() in prompts[
        ("ja", "chatgpt-codex")
    ]
    assert "{{HANDOFF_PROMPT}}" not in "".join(prompts.values())


def test_codex_source_change_does_not_change_other_routes(tmp_path: Path) -> None:
    copied_root = tmp_path / "repo"
    (copied_root / "config").mkdir(parents=True)
    shutil.copytree(ROOT / "config" / "agent-handoff", copied_root / "config" / "agent-handoff")
    before = rendered_prompts(copied_root, include_unverified=True)
    copied_handoff = copied_root / "config" / "agent-handoff" / "ja" / "codex-handoff.md"
    copied_handoff.write_text(
        copied_handoff.read_text(encoding="utf-8")
        + "\nCODEX-ONLY-CHANGE\n",
        encoding="utf-8",
    )
    after = rendered_prompts(copied_root, include_unverified=True)

    changed = {route for route in before if before[route] != after[route]}
    assert changed == {("ja", "chatgpt-codex")}


def test_chatgpt_route_never_requires_screen_transcription_or_images() -> None:
    prompts = rendered_prompts(include_unverified=True)
    japanese = prompts[("ja", "chatgpt-codex")]
    english = prompts[("en", "chatgpt-codex")]

    assert "画面の文章を転記させたり" in japanese
    assert "画像やスクリーンショットを送らせたりしない" in japanese
    assert "do not ask me to transcribe on-screen text" in english
    assert "send an image or screenshot" in english


def test_manifest_forbids_cross_agent_names() -> None:
    manifest = json.loads(
        ROOT.joinpath("config/agent-handoff/manifest.json").read_text(encoding="utf-8")
    )
    prompts = rendered_prompts(include_unverified=True)
    for language, routes in manifest["routes"].items():
        for route, config in routes.items():
            for forbidden in config["forbidden"]:
                assert forbidden not in prompts[(language, route)]


def test_every_handoff_uses_a_fixed_documents_root_and_scoped_env() -> None:
    prompts = rendered_prompts(include_unverified=True)
    expected_roots = {
        ("ja", "chatgpt-codex"): "Documents\\Codex\\NijiUnit",
        ("en", "chatgpt-codex"): "Documents\\Codex\\NijiUnit",
        ("ja", "claude-code"): "Documents\\ClaudeCode\\NijiUnit",
        ("en", "claude-code"): "Documents\\ClaudeCode\\NijiUnit",
        ("ja", "gemini-cli"): "Documents\\GeminiCLI\\NijiUnit",
        ("en", "gemini-cli"): "Documents\\GeminiCLI\\NijiUnit",
    }
    for route, text in prompts.items():
        assert expected_roots[route] in text
        assert ".env" in text
        assert "workspace" in text
