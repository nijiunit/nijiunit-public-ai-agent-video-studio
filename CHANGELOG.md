# Changelog

## Unreleased

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
