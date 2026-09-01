# Changelog

## Unreleased

- Restored the end-to-end-tested eight-stage beginner handoff for ChatGPT,
  Claude, and Gemini in Japanese and English. Each route now keeps its progress,
  announces the agent handoff, displays the exact handoff text, and guides copy,
  paste, and send as separate beginner actions while accepting natural replies.
- Stopped repeating first-time Google setup for an already configured,
  unchanged API key. Agents now open the setup page only for a missing key,
  an explicit replacement/reconfiguration request, or a failed non-generation
  connection check, and never while an update-divergence gate is blocking work.
- Added equal, beginner-first root entries for Codex (`AGENTS.md`), Claude Code
  (`CLAUDE.md`), and Gemini CLI (`GEMINI.md`). All three now route to the same
  language-matched detailed guide without making one agent's file the parent.
- Made the first-message route an explicit top-of-file gate, including the
  common `こんにちわ` spelling, and prohibited generic greeting replies that
  fail to offer the tutorial or from-scratch choice.
- Prevented private character registries and reference media from becoming
  publishable files, made small storyboard corrections reject unknown sheets
  and out-of-scope model changes, expanded video revisions through dependent
  continuity shots, and preserved every replaced clip artifact under
  `rejected/`.
- Made completion recovery discover custom project folders and accept common
  natural Japanese approvals such as `問題がありません` without confusing them
  with correction requests.
- Made every user-facing turn purposeful: the agent now continues routine work
  without acknowledgement-only stops, asks only concrete production decisions,
  accepts natural-language equivalents, and honors unambiguous conditional
  authorization such as correcting a shot and then continuing to generation.
- Changed post-review revisioning from workbook-only `_rNNN` files to immutable
  whole-run versions. Storyboard, image, video, or audio corrections now create
  the next `vNNN`, keep artifact names aligned, preserve provenance, and retain
  replaced material under the new run's `rejected/` folder. Legacy `_rNNN`
  workbooks remain readable.
- Removed routine “Opened” acknowledgement turns from artifact handoffs.
  Workbook handoff now includes opening the exact file, reviewing every sheet,
  recording yellow-field corrections and saving, or reporting approval in one
  concise instruction.
- Restored the established beginner production handoff: after story, assets,
  any required new-character identity approval, and aspect ratio, the agent
  generates and inspects all starting images internally and presents the
  image-filled Excel storyboard as the next normal user review instead of
  pausing for a standalone first-image approval.
- Clarified the Japanese and English beginner prompts for aspect-ratio and
  update choices so agents request the choice itself, reserve completion
  wording for completed operations, avoid raw HTML whitespace entities, and
  keep replies short with the conclusion or current action first.
- Added a two-route beginner story intake for NijiUnit tutorials or original
  productions, explicit disclosure that NijiUnit source character/media assets
  are not published, safe optional `sample_story.md` creation from verified
  public tutorial text, natural-language reference-file guidance, and routing
  from greetings or short requests without requiring a long prompt.
- Added image, video, and audio intake, plus a beginner character-registration
  gate that creates reviewable identity references and keeps changed versions
  pending until the user approves them.
- Added an `apply-corrections` workflow that reads the Excel correction fields,
  revises the storyboard, preserves rejected material, and produces a new
  workbook revision instead of treating extraction as the correction itself.
- Added integrated speech, soundtrack, subtitle, final-video, and video-review
  finishing, followed by a natural-language completion check and an editable,
  checksummed `history/` archive.
- Bundled a small licensed public video, its approved Excel storyboard, and
  Japanese and English offline review pages so a beginner can inspect a real
  finished example before starting a production.

## 0.7.1 - 2026-08-28

- Simplified the Japanese and English beginner Google API setup into one
  NijiUnit page: users review the numbered Google AI Studio illustration,
  open Google in a separate window, return to the same page, paste into a
  highlighted local field, and save and verify without an intermediate screen.
  Updated the Codex handoff and setup guides to launch this page immediately
  after local preparation and direct beginners to the printed local URL.

## 0.7.0 - 2026-08-27

- Added a beginner-first local browser setup page with illustrated Google AI
  Studio guidance, masked API-key storage, explicit replacement protection,
  and non-generation authentication/model verification. The page is
  loopback-only, serves its owned visual assets locally, and does not put
  secrets in chat, URLs, logs, or browser storage.
- Restricted website handoff sync to explicitly verified routes. All language
  and agent drafts now pin a dedicated Documents location, forbid temporary or
  workspace copies, and scope `.env` use to the exact target repository.
- Strengthened the public-repository safety check to scan tracked and
  non-ignored untracked candidates of every file type, reject tracked local
  environment files, and require manual review for oversized files or links.
- Added verified nijiunit YouTube tutorial sessions: safe URL and official-channel
  validation, paired website catalogs, opt-in Gemini video observation and live
  comments, untrusted-comment isolation, sequential steps, and one-time official
  subscription, milestone-thanks, and activity messages after completion.
- Added a per-production `9:16` or `16:9` choice, with the resolved dimensions
  pinned in the guidance lock for consistent prompts, review artifacts, and output.
- Made story sampling temperature optional and omit it from Gemini requests when
  the website profile does not explicitly provide it.
- Added a versioned, SHA-256-verified website-guidance channel with daily
  manifest checks, immutable caches, expiry and compatibility enforcement,
  operator notices, and per-production guidance snapshots.
- Moved current model choices, media settings, and evolving story, image,
  video, and speech guidance out of core Python into the website production
  profile, while retaining local safety and Excel approval enforcement.
- Removed work-specific story and soundtrack behavior from the generic engine;
  public samples, HOWTO movies, and deterministic sample soundtracks now live
  in the separate `nijiunit-public-ai-agent-video-studio-howto-movie`
  repository, while generic ambience accepts work-specific JSON settings.
- Restored the Excel storyboard as the mandatory human-review artifact for
  every production, with automatic workbook creation after all starting images
  exist and an explicit approval command.
- Blocked video generation until the current workbook has been approved and
  contains no unapplied correction.
- Updated Japanese and English agent instructions, user guides, workflows, and
  the public sample to make the Excel review gate visible and reproducible.
- Added beginner artifact handoff: separate `review` and `final` folders,
  non-overwriting workbook revisions, spreadsheet-app detection, offline
  Japanese and English HTML review pages, cross-platform folder reveal, clear
  headless and workbook-lock recovery, and one-action agent guidance.

## 0.6.0 - 2026-08-06

- Added matched English and Japanese entry points, setup guides, agent
  instructions, production workflows, and release documentation.
- Added automated documentation checks that keep both language routes present
  and mutually linked.
- Defined repository versioning and release responsibilities for AI agents.
- Added an automated check that keeps `pyproject.toml` and the latest released
  CHANGELOG entry consistent.
- Defined the repository's responsibility as the post-clone handoff: Python,
  FFmpeg, Google API billing, key storage, connection checks, and production.
- Added beginner-oriented Python setup guidance and an opt-in Windows Python
  installation path that requires user confirmation.
- Added a one-user-action-at-a-time Google API onboarding guide covering paid
  video requirements, project billing, secret handling, and stopping safely.
- Replaced the ambiguous `READY` state with local, online-verification, and
  paid-generation-not-tested readiness states.
- Extended online diagnostics to check the configured story, image, video, and
  TTS model identifiers without generating paid media.

## 0.5.0 - 2026-08-06

- Added a first-run Gemini API-key onboarding tool that uses hidden terminal
  input, preserves existing `.env` settings, and never prints the secret.
- Changed the AI-agent setup contract so a missing API key is reported as
  "base installation complete; user action required," not fully usable.
- Added step-by-step Google AI Studio guidance and Windows/macOS verification
  commands to the setup scripts and user documentation.
- Added an opt-in, non-generation online authentication check so agents do not
  report the app as fully usable merely because a key-shaped value exists.

## 0.4.0 - 2026-08-06

- Added root `AGENTS.md` intent routing for installation, usage questions, and
  video-production requests.
- Added idempotent Windows and macOS/Linux setup scripts that preserve `.env`
  and never call generation APIs during installation.
- Added `scripts/doctor.py` to verify Python, the editable package,
  dependencies, FFmpeg, the public character registry, demo metadata, API-key
  presence, and output access without exposing secrets.
- Added a Japanese user guide, setup troubleshooting, doctor unit tests, and
  CI coverage for linting and installation diagnostics.

## 0.3.0 - 2026-08-06

- Rebuilt the second half of `星のむこうの虹` as a continuous cloud dive,
  river chase, close waterfall pass, grass-level flight, and landing sequence.
- Added approved Mio motion references for cinematic descent and low-altitude
  flight, with explicit head/neck/body alignment and service-seam constraints.
- Added three new 16:9 scene anchors for the dive, waterfall, and low flight.
- Replaced the quiet per-shot ambience with a deterministic 30-second
  cinematic soundtrack containing wind, river, panning waterfall, spray,
  grass airflow, landing impact, dialogue ducking, and loudness reporting.
- Re-verified the completed mix with local ASR and refreshed the 90-frame
  visual contact sheet and episode-level AI model-use record.
- Made `examples/space-friends` the single public showcase and updated setup
  guidance, licenses, examples, and tests after moving the earlier prototype
  demo to a separate repository.

## 0.2.0 - 2026-08-05

- Added the 30-second `星のむこうの虹` public demo with four approved scene
  anchors and ten three-second shots.
- Added Mio/Lux v002 motion references for zero-gravity flight, controlled
  descent, soft landing, companion flight, and invitation light pulses.
- Added per-shot TTS voice configuration and a deterministic
  `space-to-nature` ambience profile.
- Recorded shot-level model use, rejected takes, local ASR verification, and
  90-frame visual inspection.

## 0.1.0 - 2026-08-05

- Initial public-safe extraction of the three-second storyboard workflow.
- Added versioned character registry, design-motion references, continuity from
  the prior clip's final frame, and a fully fictional Mio/Lux sample.
- Added asset provenance fields and secret-safe repository defaults.
