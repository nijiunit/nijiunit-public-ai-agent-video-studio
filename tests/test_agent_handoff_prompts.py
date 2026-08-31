from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.sync_agent_handoff_prompts import ROOT, rendered_prompts


def test_all_six_verified_routes_are_publishable() -> None:
    assert set(rendered_prompts()) == {
        ("ja", "chatgpt-codex"),
        ("ja", "claude-code"),
        ("ja", "gemini-cli"),
        ("en", "chatgpt-codex"),
        ("en", "claude-code"),
        ("en", "gemini-cli"),
    }


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


def test_every_route_tracks_six_stage_progress_without_guessing_screens() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "全6段階" in text
            assert "進行状況：段階◯／全6" in text
            assert "段階6" in text
        else:
            assert "six stages" in text
            assert "Progress: stage N of 6" in text
            assert "stage 6" in text


def test_every_route_hands_off_immediately_without_acknowledgement_turns() -> None:
    prompts = rendered_prompts(include_unverified=True)
    for language, route in prompts:
        text = prompts[(language, route)]
        if language == "ja":
            assert "この返信をすべてコピーし" in text
            assert "コピー、貼り付け、送信ごとの完了報告を求めません" in text
            assert "引き継ぎ文章を表示してください" not in text
            assert "コピーしました」と返したら" not in text
            assert "貼り付けました」と返ったら" not in text
        else:
            assert "Copy this entire reply" in text
            assert "Do not ask for separate Copied, Pasted, or Sent acknowledgements" in text
            assert "Show the handoff text" not in text
            assert 'After I reply "Copied"' not in text


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
