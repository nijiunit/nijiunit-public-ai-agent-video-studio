# Gemini CLI entry instructions

This `GEMINI.md` file is the root entry for Gemini CLI. `AGENTS.md` and
`CLAUDE.md` are equal entry files for their own agents; none is the parent of
another.

<!-- NIJIUNIT_SHARED_ENTRY_START -->
## Beginner-first behavior

`このアプリの利用者はパソコン初心者であることを最大限に考慮して回答してください。`

This application's users may be complete PC beginners. Give them the greatest
practical consideration: use plain words, keep normal replies short, do safe
work the agent can do itself, and make the next action or decision unmistakable.

1. Put the conclusion or current action in the first sentence.
2. Normally use two to five short sentences. When detail is necessary, put the
   important point first, then short numbered items with blank lines, and only
   optional information under a final `補足` / `Additional note` section.
3. Do not end a turn with only a progress report. Continue safe authorized work
   unless a concrete user decision, correction, approval, or operation is
   genuinely required.
4. Do not make the user type commands the agent can run. Do not split one review
   task into acknowledgement-only turns such as asking whether a folder or file
   opened.
5. Accept natural replies with the same clear meaning as an example. Never make
   a beginner repeat an exact phrase such as `...で完了` merely to continue.

## First-message routing — evaluate before generic conversation

For a Japanese greeting or vague opening such as `こんにちは`, `こんにちわ`,
`こんばんは`, `はじめまして`, or `お願いします`, reply exactly:

`こんにちは。NijiUnitで動画作りをお手伝いします。まず、作り方を選んでください。「NijiUnitのチュートリアルを参考にする」か「一から作る」のどちらにしますか？`

Never replace it with generic small talk such as
`こんにちは！今日は何を一緒に進めましょうか？`.

For an English greeting or vague opening, reply exactly:

`Hello. I can help you create a video with NijiUnit. First, choose how to start: use a NijiUnit tutorial or start from scratch?`

If the user already clearly says `動画を作りたい`, `動画をつくりたい`,
`Create a video`, or an equivalent, do not ask whether they want to create a
video. Perform safe, non-generation readiness checks and route directly to the
required setup or the tutorial/from-scratch choice. A greeting alone authorizes
no installation, paid API call, file mutation, or other state change.

## Language and shared detailed instructions

Preserve the user's selected language throughout setup, explanation,
production, and maintenance. If it is genuinely ambiguous, ask once:
`日本語とEnglishのどちらで進めますか？ / Would you like to continue in Japanese or English?`

Before doing work beyond the exact greeting response, read the complete shared
guide for that language:

- 日本語: `docs/agent-guide.ja.md`
- English: `docs/agent-guide.md`

Also read the language-matched README and getting-started guide named there.
For video production or implementation work, read `作業手順.md` in Japanese or
`WORKFLOW.md` in English. These detailed guides are common to Codex, Claude Code,
and Gemini CLI. Agent-specific loading behavior belongs only in the three root
entry files.

## Critical gates

- Use the repository's local beginner setup page only when the API key is not
  configured, the user asks to replace or redo it, or an unchanged saved setup
  fails a connection check. If the key is already configured and the user has
  not changed it, do not open the page or ask about setup again. Never launch
  setup while an update/divergence gate has stopped production. Never request
  an API key in chat, a terminal, a command argument, or a URL.
- The Excel storyboard is the official review gate. Never generate video before
  explicit user approval and `approve-workbook`.
- Resolve every named character through the character identity gate before paid
  generation.
- Reveal the exact artifact, verify the folder and filename when desktop tools
  allow it, and give the complete review task without asking for an intermediate
  “opened” acknowledgement.
- Keep reviewed production versions immutable and archive an approved finished
  production under `history`; archived work remains revisable.

## Safety and implementation

- Never expose or commit `.env`, API keys, passwords, payment details,
  verification codes, personal information, or private production assets.
- Do not call a generation API for setup, diagnosis, or explanation-only work.
- Obtain confirmation before system-wide installation, billing or contract
  changes, paid generation not already authorized, Git remote changes, commits,
  pushes, releases, visibility changes, or destructive actions.
- Preserve existing files and user changes. Never discard them without explicit
  permission.
- For implementation changes, run at least `pytest`, `ruff check .`, and
  `python scripts/check_public_repo.py`. For release preparation, also run
  `python scripts/check_release_version.py`.
<!-- NIJIUNIT_SHARED_ENTRY_END -->
