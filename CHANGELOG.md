# Changelog

## Unreleased

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
