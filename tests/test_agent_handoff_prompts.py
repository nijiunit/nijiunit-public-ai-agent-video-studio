from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.sync_agent_handoff_prompts import ROOT, rendered_prompts


def test_all_six_verified_routes_are_publishable() -> None:
    assert set(rendered_prompts()) == {
        ("ja", "chatgpt-codex"),
        ("ja", "claude-code"),
        ("ja", "google-antigravity"),
        ("en", "chatgpt-codex"),
        ("en", "claude-code"),
        ("en", "google-antigravity"),
    }


def test_six_agent_language_routes_are_independent() -> None:
    prompts = rendered_prompts(include_unverified=True)
    assert set(prompts) == {
        ("ja", "chatgpt-codex"),
        ("ja", "claude-code"),
        ("ja", "google-antigravity"),
        ("en", "chatgpt-codex"),
        ("en", "claude-code"),
        ("en", "google-antigravity"),
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


def test_every_route_never_requires_screen_transcription_or_images() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "画面の文章を転記させたり" in text
            assert "画像やスクリーンショットを送らせたりしない" in text
        else:
            assert "do not ask me to transcribe on-screen text" in text
            assert "send an image or screenshot" in text


def test_every_route_tracks_eight_stage_progress_without_guessing_screens() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "全8段階" in text
            assert "進行状況：段階◯／全8" in text
            assert "段階6" in text
            assert "段階7" in text
            assert "段階8" in text
            assert "現在地を見失った場合は推測で進めず" in text
        else:
            assert "eight stages" in text
            assert "Progress: stage N of 8" in text
            assert "stage 6" in text
            assert "stage 7" in text
            assert "stage 8" in text
            assert "If you lose the current stage, do not guess" in text


def test_every_route_guides_the_verified_show_copy_paste_send_sequence() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "担当交代を伝える" in text
            assert "引き継ぎ文章を表示する" in text
            assert "この文章をすべてコピーしてください" in text
            assert "入力欄へ貼り付ける一操作だけ" in text
            assert "送信" in text
            assert "同じ意味の自然な返事を受け付け" in text
            assert "返答をこの案内AIへ転記させません" in text
        else:
            assert "Announce the handoff" in text
            assert "Display the" in text and "handoff" in text
            assert "Copy this entire message" in text
            assert "give only the action to paste it" in text
            assert "give only the action to" in text and "send" in text
            assert "Accept any natural reply with the same meaning" in text
            assert "response back here" in text


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
        ("ja", "google-antigravity"): "Documents\\Antigravity\\NijiUnit",
        ("en", "google-antigravity"): "Documents\\Antigravity\\NijiUnit",
    }
    for route, text in prompts.items():
        assert expected_roots[route] in text
        assert ".env" in text
        assert "workspace" in text


def test_antigravity_handoff_uses_the_workspace_rule() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language in ("ja", "en"):
        text = prompts[(language, "google-antigravity")]
        assert ".agents/rules/nijiunit.md" in text
        assert "GEMINI.md" in text
        assert "Gemini CLI" not in text


def test_every_handoff_skips_unchanged_setup_and_uses_the_local_page_when_needed() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "APIキーが設定済み" in text
            assert (
                "初回設定画面を起動せず" in text
                or "「NijiUnit 初回設定」を起動せず" in text
            )
            assert "普段使っているブラウザのアドレス欄へ貼り付けて" in text
            assert "「開いた」というチャット返信を求め" in text
        else:
            assert "API key is" in text
            assert "do not launch" in text or "do not open first-time setup" in text
            assert "address bar of the browser you normally use" in text
            assert "ask me to reply that it opened" in text
