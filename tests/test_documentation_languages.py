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
    ("templates/story-input.md", "templates/story-input.ja.md"),
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
    assert "Mandatory Excel storyboard gate" in instructions
    assert "approve-workbook" in instructions


def test_beginner_setup_page_starts_google_setup() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_handoff = (ROOT / "config/agent-handoff/ja/codex-handoff.md").read_text(
        encoding="utf-8"
    )
    english_handoff = (ROOT / "config/agent-handoff/en/codex-handoff.md").read_text(
        encoding="utf-8"
    )

    assert "Immediately after the local runtime reaches `LOCAL READY`" in instructions
    assert "まずリポジトリの手順に従ってローカルの「NijiUnit 初回設定」画面を起動" in japanese_handoff
    assert "次のURLをコピーし、普段お使いのブラウザのアドレス欄へ貼り付けて" in japanese_handoff
    assert "次のURLをクリックしてください" not in japanese_handoff
    assert "「開いた」というチャット返信を求めず" in japanese_handoff
    assert "First follow the repository instructions to launch" in english_handoff
    assert "Copy the following URL and paste it into the address bar" in english_handoff
    assert "Click the following URL" not in english_handoff
    assert "Do not ask me to reply that it opened" in english_handoff


def test_beginner_choices_do_not_masquerade_as_completed_operations() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_guide = (ROOT / "docs/basic-operation.ja.md").read_text(
        encoding="utf-8"
    )
    english_guide = (ROOT / "docs/basic-operation.md").read_text(encoding="utf-8")

    assert "「横長」または「縦長」と返信してください" in instructions
    assert "「更新する」または「今回は更新しない」と返信してください" in instructions
    assert "Reply “Horizontal” or “Vertical.”" in instructions
    assert "Reply “Update” or “Continue without updating.”" in instructions
    assert "選択肢そのものを返信します" in japanese_guide
    assert 'reply with the choice itself; do not add "complete."' in english_guide
    assert "通常の回答は短く、最初に結論または今すること" in japanese_guide
    assert "two to five short sentences" in instructions
    assert "a final `補足` / `Additional note` section" in instructions
    assert "Put the most important conclusion or current action" in instructions

    checked_files = (
        "AGENTS.md",
        "docs/basic-operation.ja.md",
        "docs/basic-operation.md",
        "作業手順.md",
        "WORKFLOW.md",
        "docs/agent-guide.ja.md",
        "docs/agent-guide.md",
        "config/runtime-guidance/agent_guide_ja.md",
        "config/runtime-guidance/agent_guide_en.md",
    )
    forbidden_prompts = ("16:9で完了", "9:16で完了", "更新して完了")
    for relative in checked_files:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for forbidden in forbidden_prompts:
            assert forbidden not in text, f"forbidden prompt in {relative}: {forbidden}"


def test_beginner_story_intake_has_two_routes_and_private_asset_disclosure() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_guide = (ROOT / "docs/basic-operation.ja.md").read_text(
        encoding="utf-8"
    )
    input_readme = (ROOT / "input/README.md").read_text(encoding="utf-8")

    assert "NijiUnitのチュートリアルを参考にする" in instructions
    assert "一から作る" in instructions
    assert "input/sample_story.md" in instructions
    assert "キャラクター画像・動画・音声は公開していません" in instructions
    assert "題材を普通の言葉で伝える" in japanese_guide
    assert "利用者がMarkdownを手作業で書く必要はありません" in input_readme
    assert "説明が足りないところは、AIエージェントから一つずつ確認します" in instructions
    assert "sample_story.md" in input_readme
    assert "本番用には使いません" in input_readme


def test_short_first_messages_route_into_nijiunit_without_a_long_prompt() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_guide = (ROOT / "docs/basic-operation.ja.md").read_text(
        encoding="utf-8"
    )
    english_guide = (ROOT / "docs/basic-operation.md").read_text(encoding="utf-8")

    assert "Mandatory first-message routing" in instructions
    assert "こんにちは。NijiUnitで動画作りをお手伝いします" in instructions
    assert "「動画を作る」または「使い方を知る」" in instructions
    assert "動画を作りたい" in instructions
    assert "whether they want to create a video" in instructions
    assert "特別なコマンドや長い依頼文は不要です" in japanese_guide
    assert "No special command or long copied prompt is required" in english_guide
