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

## Non-negotiable safety rules

- Never expose or commit `.env`, API keys, passwords, payment details, verification codes, personal information, or private production assets.
- Do not call a generation API for setup, diagnosis, or explanation-only requests.
- Explain and obtain confirmation before installing system software or changing contracts, billing, automatic payments, Git remotes, tags, releases, or repository visibility.
- Never discard existing files or user changes without explicit permission.
- For implementation changes, run at least `pytest`, `ruff check .`, and `python scripts/check_public_repo.py`.
- For release preparation, also run `python scripts/check_release_version.py`.
