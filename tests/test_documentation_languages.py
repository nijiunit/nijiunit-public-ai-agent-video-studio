from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
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


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _shared_entry(text: str) -> str:
    start = "<!-- NIJIUNIT_SHARED_ENTRY_START -->"
    end = "<!-- NIJIUNIT_SHARED_ENTRY_END -->"
    return text.split(start, 1)[1].split(end, 1)[0]


def test_required_language_pairs_exist_and_link_to_each_other() -> None:
    for english_relative, japanese_relative in LANGUAGE_PAIRS:
        english = ROOT / english_relative
        japanese = ROOT / japanese_relative

        assert english.is_file(), f"missing English guide: {english_relative}"
        assert japanese.is_file(), f"missing Japanese guide: {japanese_relative}"

        english_text = english.read_text(encoding="utf-8")
        japanese_text = japanese.read_text(encoding="utf-8")
        assert japanese.name in english_text
        assert english.name in japanese_text


def test_three_agents_have_equal_short_entries_and_one_shared_guide() -> None:
    entries = {relative: _text(relative) for relative in ENTRY_FILES}
    shared = [_shared_entry(text) for text in entries.values()]

    assert shared[0] == shared[1] == shared[2]
    for relative, instructions in entries.items():
        assert len(instructions.encode("utf-8")) <= 32 * 1024
        assert len(instructions.splitlines()) < 200
        assert "docs/agent-guide.md" in instructions
        assert "docs/agent-guide.ja.md" in instructions
        assert "complete PC beginners" in instructions
        assert "このアプリの利用者はパソコン初心者であることを最大限に考慮" in instructions
        assert "日本語とEnglishのどちらで進めますか？" in instructions
        assert "approve-workbook" in instructions
        assert "CLAUDE.md" in instructions
        assert "GEMINI.md" in instructions
        assert "AGENTS.md" in instructions
        assert "parent of" in instructions
        assert "@AGENTS.md" not in instructions, relative

    japanese_guide = _text("docs/agent-guide.ja.md")
    english_guide = _text("docs/agent-guide.md")
    for filename in ENTRY_FILES:
        assert filename in japanese_guide
        assert filename in english_guide
    assert "3つの入口は対等" in japanese_guide
    assert "None of those entry files is the parent" in english_guide


def test_agent_handoffs_use_the_matching_root_entry() -> None:
    expected = {
        "config/agent-handoff/ja/codex-handoff.md": "AGENTS.md",
        "config/agent-handoff/en/codex-handoff.md": "AGENTS.md",
        "config/agent-handoff/ja/claude-code-handoff.md": "CLAUDE.md",
        "config/agent-handoff/en/claude-code-handoff.md": "CLAUDE.md",
        "config/agent-handoff/ja/gemini-cli-handoff.md": "GEMINI.md",
        "config/agent-handoff/en/gemini-cli-handoff.md": "GEMINI.md",
    }
    for relative, entry in expected.items():
        assert entry in _text(relative)

    assert "`AGENTS.md`をClaude Codeの入口として使いません" in _text(
        "config/agent-handoff/ja/claude-code-handoff.md"
    )
    assert "`AGENTS.md`をGemini CLIの入口として使いません" in _text(
        "config/agent-handoff/ja/gemini-cli-handoff.md"
    )


def test_short_first_messages_route_into_nijiunit_without_a_long_prompt() -> None:
    for relative in ENTRY_FILES:
        instructions = _text(relative)
        assert instructions.index("First-message routing") < instructions.index(
            "Language and shared detailed instructions"
        )
        assert "こんにちわ" in instructions
        assert "こんにちは。NijiUnitで動画作りをお手伝いします" in instructions
        assert "「NijiUnitのチュートリアルを参考にする」か「一から作る」" in instructions
        assert "今日は何を一緒に進めましょうか" in instructions
        assert "Never replace it with generic small talk" in instructions
        assert "動画を作りたい" in instructions
        assert "use a NijiUnit tutorial or start from scratch" in instructions

    assert "特別なコマンドや長い依頼文は不要です" in _text(
        "docs/basic-operation.ja.md"
    )
    assert "No special command or long copied prompt is required" in _text(
        "docs/basic-operation.md"
    )


def test_beginner_setup_page_starts_only_when_configuration_needs_it() -> None:
    japanese_guide = _text("docs/agent-guide.ja.md")
    english_guide = _text("docs/agent-guide.md")
    japanese_handoff = _text("config/agent-handoff/ja/codex-handoff.md")
    english_handoff = _text("config/agent-handoff/en/codex-handoff.md")

    assert "open_setup.py --language ja" in japanese_guide
    assert "open_setup.py --language en" in english_guide
    assert "設定済みで私が変更していなければ" in japanese_handoff
    assert "初回設定」を起動せず" in japanese_handoff
    assert "If it is configured and I have not changed it" in english_handoff
    assert "do not launch “NijiUnit First-time Setup" in english_handoff
    assert "次のURLをコピーし、普段お使いのブラウザのアドレス欄へ貼り付けて" in japanese_handoff
    assert "次のURLをクリックしてください" not in japanese_handoff
    assert "「開いた」というチャット返信を求めず" in japanese_handoff
    assert "Copy the following URL and paste it into the address bar" in english_handoff
    assert "Click the following URL" not in english_handoff
    assert "Do not ask me to reply that it opened" in english_handoff

    for relative in ENTRY_FILES:
        instructions = _text(relative)
        assert "If the key is already configured and the user has" in instructions
        assert "do not open the page or ask about setup again" in instructions
        assert "update/divergence gate" in instructions

    assert "保存済みで利用者が変更していなければ、初回設定画面を開かず" in japanese_guide
    assert "do not open the first-time setup page" in english_guide
    assert "An existing unchanged API setup does not need to be repeated" in _text(
        "scripts/setup.ps1"
    )
    assert "An existing unchanged API setup does not need to be repeated" in _text(
        "scripts/setup.sh"
    )


def test_beginner_choices_and_response_wording_are_clear() -> None:
    japanese_workflow = _text("作業手順.md")
    english_workflow = _text("WORKFLOW.md")
    entries = "\n".join(_text(relative) for relative in ENTRY_FILES)

    assert "「横長」または「縦長」と返信してください" in japanese_workflow
    assert "「更新する」または「今回は更新しない」と返信してください" in japanese_workflow
    assert "Reply ‘Horizontal’ or ‘Vertical.’" in english_workflow
    assert "Reply ‘Update’ or ‘Continue without updating.’" in english_workflow
    assert "two to five short sentences" in entries
    assert "final `補足` / `Additional note` section" in entries
    assert "Put the conclusion or current action" in entries

    checked_files = ENTRY_FILES + (
        "docs/basic-operation.ja.md",
        "docs/basic-operation.md",
        "作業手順.md",
        "WORKFLOW.md",
        "docs/agent-guide.ja.md",
        "docs/agent-guide.md",
        "config/runtime-guidance/agent_guide_ja.md",
        "config/runtime-guidance/agent_guide_en.md",
    )
    for relative in checked_files:
        text = _text(relative)
        for forbidden in ("16:9で完了", "9:16で完了", "更新して完了"):
            assert forbidden not in text, f"forbidden prompt in {relative}: {forbidden}"


def test_beginner_story_intake_has_two_routes_and_private_asset_disclosure() -> None:
    japanese_guide = _text("docs/agent-guide.ja.md")
    input_readme = _text("input/README.md")

    assert "NijiUnitのチュートリアルを参考にする" in japanese_guide
    assert "一から作る" in japanese_guide
    assert "input/sample_story.md" in japanese_guide
    assert "キャラクター画像・動画・音声は公開していません" in japanese_guide
    assert "説明が足りないところは、AIエージェントから一つずつ確認します" in japanese_guide
    assert "利用者がMarkdownを手作業で書く必要はありません" in input_readme
    assert "本番用には使いません" in input_readme


def test_conversation_turns_have_a_decision_or_continue_work() -> None:
    english_guide = _text("docs/agent-guide.md")
    japanese_guide = _text("docs/agent-guide.ja.md")
    runtime_ja = _text("config/runtime-guidance/agent_guide_ja.md")

    assert "Every user-facing turn must either continue" in english_guide
    assert "conditional authorization" in english_guide
    assert "制作に必要な情報は揃っています" in japanese_guide
    assert "途中報告だけでターンを終えません" in runtime_ja
    assert "質問がなければ先へ進みます" in runtime_ja


def test_new_revisions_use_whole_run_versions() -> None:
    english_guide = _text("docs/agent-guide.md")
    japanese_workflow = _text("作業手順.md")
    architecture = _text("docs/architecture.md")
    troubleshooting = _text("docs/troubleshooting.md")

    assert "whole `vNNN` run" in english_guide
    assert "Legacy `_r002`" in english_guide
    assert "`v002`" in japanese_workflow
    assert "complete production run" in architecture
    assert "next whole run" in troubleshooting
    assert "`storyboard_vNNN.xlsx`" in architecture
    assert "not created for new productions" in architecture


def test_normal_production_moves_from_assets_to_excel_without_single_image_gate() -> None:
    japanese_workflow = _text("作業手順.md")
    english_workflow = _text("WORKFLOW.md")
    japanese_guide = _text("docs/getting-started.ja.md")
    english_guide = _text("docs/getting-started.md")
    profile = _text("config/runtime-guidance/production_profile.json")

    assert "次に利用者へ見せる正式な確認物はExcelコンテ" in japanese_workflow
    assert "the workbook is the next user-facing review" in english_workflow
    assert "通常制作では画像1枚だけを利用者へ見せて返答を待ちません" in japanese_guide
    assert "Normal production does not pause for the user's approval of one" in english_guide

    checked = (japanese_workflow, english_workflow, japanese_guide, english_guide, profile)
    for text in checked:
        for phrase in (
            "Generate and review only the first starting image",
            "Review the first generated keyframe with the user",
            "最初の開始画像を1枚だけ生成し",
            "最初から全画像を生成せず、まず1枚だけ確認します",
        ):
            assert phrase not in text


def test_artifact_review_does_not_pause_for_opened_acknowledgement() -> None:
    japanese_workflow = _text("作業手順.md")
    english_workflow = _text("WORKFLOW.md")
    japanese_guide = _text("docs/agent-guide.ja.md")
    english_guide = _text("docs/agent-guide.md")
    runtime_ja = _text("config/runtime-guidance/agent_guide_ja.md")
    runtime_en = _text("config/runtime-guidance/agent_guide_en.md")

    assert "「開いた」という中間報告では止めない" in japanese_workflow
    assert "intermediate “Opened” acknowledgement" in english_workflow
    assert "通常操作ごとの完了報告は求めません" in japanese_guide
    assert "do not wait for acknowledgements merely for opening" in english_guide
    assert "Excelなら、開く、全シートを確認する" in runtime_ja
    assert "For Excel, include opening it, reviewing every sheet" in runtime_en

    checked = (
        japanese_workflow,
        english_workflow,
        japanese_guide,
        english_guide,
        runtime_ja,
        runtime_en,
    )
    for text in checked:
        for phrase in (
            "利用者へ一操作だけ伝えて待つ",
            "Reveal the artifact and give the beginner one action, then wait.",
            "Excelが開いたら、開いたことを教えてください",
            "After the workbook opens, guide the first sheet",
        ):
            assert phrase not in text
