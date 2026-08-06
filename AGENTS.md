# Instructions for AI agents

These instructions apply to the entire repository. This repository takes over after the upstream guide has installed an AI agent and Git, cloned the repository, and opened this folder.

## Preserve the user's language

The upstream guide offers Japanese and English. Continue in that selected language throughout setup, explanation, production, and maintenance.

1. If the upstream request or the user explicitly selected a language, preserve it.
2. Otherwise, reply in the language used by the user's request.
3. If the language is genuinely ambiguous, ask once: `日本語とEnglishのどちらで進めますか？ / Would you like to continue in Japanese or English?`
4. Do not ask again after the language is known, and do not mix languages except for exact UI labels, commands, filenames, model identifiers, and diagnostic states.
5. Explain English terminal output in Japanese for a Japanese user. Keep exact commands unchanged.

Before acting, read the complete guide for the selected language:

- English: `docs/agent-guide.md`
- 日本語: `docs/agent-guide.ja.md`

Also read the language-matched README and getting-started guide named there. For video production or implementation work, read `WORKFLOW.md` in English or `作業手順.md` in Japanese.

## Mandatory Excel storyboard gate

The Excel workbook is the official human review interface for every production. `storyboard.json` is machine input and Markdown is supplementary documentation; neither replaces the Excel storyboard.

For every new video, the AI agent must follow this order:

1. Create the three-second storyboard JSON.
2. Generate and review the starting images, first one image and then the remainder.
3. Build `storyboard_<version>.xlsx` with every shot's main image, description, audio plan, nine-frame plan, review state, and correction field.
4. Reveal the workbook in its containing folder, select it, give the user one
   opening action, and stop before video generation.
5. If the user requests corrections, read or extract the Excel corrections, update the storyboard or images, rebuild the workbook, and request review again.
6. Only after the user explicitly approves the Excel storyboard, run `approve-workbook` and then generate video clips.
7. After generation, build the video-review workbook containing nine real frames per shot.

Never mark a workbook approved based only on its existence, infer approval from silence, bypass the workbook gate, or generate video while any sheet is `未確認`, `修正必要`, or contains an unapplied correction. If the user approves the storyboard in chat, the agent may run `approve-workbook` on the user's behalf; it must not do so before that explicit approval.

## Mandatory beginner artifact handoff

Never finish a production step with only a Markdown link, path, command output,
test count, or list of changed files. A beginner must be taken to the actual
artifact and given one concrete action.

1. Keep user-facing review artifacts in `review/`, finished media and final
   records in `final/`, machine files in their existing internal folders, and
   rejected material in `rejected/`.
2. Build both Japanese and English offline HTML review pages beside every
   storyboard workbook and video-frame workbook. Excel remains the official
   record; HTML is the no-spreadsheet-app review option.
3. Detect Excel, LibreOffice Calc, or Numbers. Do not require a user to buy or
   install Excel solely to inspect a storyboard. When no spreadsheet app is
   found, reveal the language-matched local HTML page instead.
4. After creating an artifact, use `run_storyboard.py reveal-artifact` for a
   production run or `scripts/reveal_artifact.py --path ...` for another exact
   file. These commands open Explorer/Finder/the desktop file manager and select
   the artifact where the OS supports selection. On Linux, give the exact
   filename in the opened folder. They do not open the application automatically.
5. When the folder opens, tell the user only the next action, for example:
   `青く選択されたファイルをダブルクリックしてください。開いたら「開いた」と返してください。`
   Wait for that reply before explaining workbook tabs, yellow correction
   fields, saving, or the next stage.
6. If the desktop cannot be opened, state that plainly, show the exact folder
   and filename, and give one manual action. Do not pretend the folder opened.
7. Never overwrite an existing review workbook. Create `_r002`, `_r003`, and so
   on. If Excel has locked a workbook, ask the user to save and close it, then
   wait for `閉じた` or the language-equivalent reply.
8. After the user opens an Excel storyboard, guide them through one sheet tab,
   the review status, the yellow correction field, and saving, one action at a
   time. When HTML is used, have them review each card and paste its generated
   summary into chat. Explicit approval in chat still authorizes
   `approve-workbook`; HTML never bypasses the Excel approval gate.
9. Apply the same reveal-and-one-action handoff to the final video, generated
   video review, and AI model-use record. In completion reports, lead with what
   the user can now open or review; keep implementation and test details
   secondary.

## Non-negotiable safety rules

- Never expose or commit `.env`, API keys, passwords, payment details, verification codes, personal information, or private production assets.
- Do not call a generation API for setup, diagnosis, or explanation-only requests.
- Explain and obtain confirmation before installing system software or changing contracts, billing, automatic payments, Git remotes, tags, releases, or repository visibility.
- Never discard existing files or user changes without explicit permission.
- For implementation changes, run at least `pytest`, `ruff check .`, and `python scripts/check_public_repo.py`.
- For release preparation, also run `python scripts/check_release_version.py`.
