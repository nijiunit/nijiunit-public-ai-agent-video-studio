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
    assert "「NijiUnitのチュートリアルを参考にする」か「一から作る」" in instructions
    assert "動画を作りたい" in instructions
    assert "Use a NijiUnit tutorial" in instructions
    assert "特別なコマンドや長い依頼文は不要です" in japanese_guide
    assert "No special command or long copied prompt is required" in english_guide


def test_conversation_turns_have_a_decision_or_continue_work() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_workflow = (ROOT / "作業手順.md").read_text(encoding="utf-8")
    runtime_ja = (ROOT / "config/runtime-guidance/agent_guide_ja.md").read_text(
        encoding="utf-8"
    )

    assert "Every user-facing turn must have a clear purpose" in instructions
    assert "質問がなければ先へ進み" in japanese_workflow
    assert "途中報告だけでターンを終えません" in japanese_workflow
    assert "質問がなければ先へ進みます" in runtime_ja
    assert "制作に必要な情報は揃っています" in instructions
    assert "conditional authorization" in instructions


def test_new_revisions_use_whole_run_versions() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    troubleshooting = (ROOT / "docs/troubleshooting.md").read_text(
        encoding="utf-8"
    )

    assert "whole `vNNN` run" in instructions
    assert "complete production run" in architecture
    assert "next whole run" in troubleshooting
    assert "Legacy `_r002`" in instructions
    assert "Legacy `_r002`" in architecture
    assert "Legacy `_r002`" in troubleshooting
    assert "v002" in instructions
    assert "v002" in architecture
    assert "v002" in troubleshooting
    assert "`storyboard_vNNN.xlsx`" in architecture
    assert "not created for new productions" in architecture


def test_normal_production_moves_from_assets_to_excel_without_single_image_gate(
) -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_workflow = (ROOT / "作業手順.md").read_text(encoding="utf-8")
    english_workflow = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")
    japanese_guide = (ROOT / "docs/getting-started.ja.md").read_text(
        encoding="utf-8"
    )
    english_guide = (ROOT / "docs/getting-started.md").read_text(
        encoding="utf-8"
    )
    profile = (ROOT / "config/runtime-guidance/production_profile.json").read_text(
        encoding="utf-8"
    )

    assert "user-facing review is the official Excel storyboard" in instructions
    assert "次に利用者へ見せる正式な確認物はExcelコンテ" in japanese_workflow
    assert "the workbook is the next user-facing review" in english_workflow
    assert (
        "通常制作では画像1枚だけを利用者へ見せて返答を待ちません"
        in japanese_guide
    )
    assert (
        "Normal production does not pause for the user's approval of one"
        in english_guide
    )

    forbidden = (
        "Generate and review only the first starting image",
        "Review the first generated keyframe with the user",
        "最初の開始画像を1枚だけ生成し",
        "最初から全画像を生成せず、まず1枚だけ確認します",
    )
    checked = (
        instructions,
        japanese_workflow,
        english_workflow,
        japanese_guide,
        english_guide,
        profile,
    )
    for text in checked:
        for phrase in forbidden:
            assert phrase not in text


def test_artifact_review_does_not_pause_for_opened_acknowledgement() -> None:
    instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    japanese_workflow = (ROOT / "作業手順.md").read_text(encoding="utf-8")
    english_workflow = (ROOT / "WORKFLOW.md").read_text(encoding="utf-8")
    japanese_guide = (ROOT / "docs/agent-guide.ja.md").read_text(
        encoding="utf-8"
    )
    english_guide = (ROOT / "docs/agent-guide.md").read_text(encoding="utf-8")
    runtime_ja = (ROOT / "config/runtime-guidance/agent_guide_ja.md").read_text(
        encoding="utf-8"
    )
    runtime_en = (ROOT / "config/runtime-guidance/agent_guide_en.md").read_text(
        encoding="utf-8"
    )

    assert "Do not pause for an opening acknowledgement" in instructions
    assert "「開いた」という中間報告では止めない" in japanese_workflow
    assert "intermediate “Opened” acknowledgement" in english_workflow
    assert "通常操作ごとの完了報告は求めません" in japanese_guide
    assert "do not wait for acknowledgements merely for opening" in english_guide
    assert "Excelなら、開く、全シートを確認する" in runtime_ja
    assert "For Excel, include opening it, reviewing every sheet" in runtime_en

    forbidden = (
        "利用者へ一操作だけ伝えて待つ",
        "Reveal the artifact and give the beginner one action, then wait.",
        "Excelが開いたら、開いたことを教えてください",
        "After the workbook opens, guide the first sheet",
    )
    checked = (
        instructions,
        japanese_workflow,
        english_workflow,
        japanese_guide,
        english_guide,
        runtime_ja,
        runtime_en,
    )
    for text in checked:
        for phrase in forbidden:
            assert phrase not in text
