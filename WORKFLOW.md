English | [日本語](作業手順.md)

# AI video production workflow (public edition)

Last updated: 2026-08-06  
Method: versioned character registry, dedicated design videos, and continuous three-second generation

## 1. Core principles

Every production starts in `input`. For a recurring character, the active version under `characters` is authoritative. Identity is stabilized in four layers.

| Layer | What it fixes | Data |
|---|---|---|
| Appearance registry | Face, shape, build, colors, clothing, materials, prohibited changes | `profile.json`, approved identity images |
| Neutral presence | Blinking, breathing, resting posture, weight of motion | `design_presence.mp4`, three keyframes |
| Signature motion | Surprise, repair, greeting, and other characteristic actions | Motion MP4, timing, three keyframes |
| Shot continuity | Position, pose, and lighting across a three-second boundary | Final frame of the previous clip |

An approved design video must be newly generated for that character from the approved appearance. Do not use a crop from an old production, a looped still image, or artificially stretched footage.

## 2. First-time setup

Prefer the platform setup script documented in the getting-started guide. The equivalent manual Windows commands are:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Store API keys only in `.env`. Never put them in chat, Markdown, JSON, Excel, logs, screenshots, or command arguments.

## 3. Build the character registry

Copy `templates/character-profile.json` and `templates/character-registry.json` into `characters/<id>/<version>`. When a face or fundamental design changes, do not overwrite the old version. Create a new version such as `v002`, review it, and then change `active_version`.

A publishable character also requires:

- `source_type`: one of `original`, `generated`, or `third_party`
- `asset_license`: usage terms
- `publishable`: `true` only after publication review
- `source_notes`: creation date, generation method, source references, and excluded rights-controlled material

Generate and validate the neutral-presence and signature-motion videos.

```powershell
.\.venv\Scripts\python.exe scripts\generate_character_design_videos.py `
  --registry-dir characters
.\.venv\Scripts\python.exe run_storyboard.py prepare-motions `
  --registry-dir characters --overwrite
.\.venv\Scripts\python.exe run_storyboard.py validate-characters `
  --registry-dir characters
.\.venv\Scripts\python.exe scripts\validate_character_design_videos.py `
  --registry-dir characters
```

The approved technical specification is 3.00 seconds, 1280×720, 24 fps, 16:9, and nine review frames extracted from the real video. A human must verify stable appearance and visible intended motion across the full clip.

## 4. Prepare `input`

At minimum, `input/story.md` describes:

- characters and their goal
- events, final payoff, and any intended lesson
- exact dialogue and speaker assignment
- visual style and framing
- settings that must not change
- exact text that must appear

Record the source and usage terms for every asset. Do not override a recurring character with an older project-specific image.

## 5. Create the three-second structure

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create
```

Limit one shot to one meaning and one primary action. Do not compress walking, explaining, operating equipment, surprise, and payoff into the same three seconds. Dialogue must be short enough to speak naturally within the actual duration.

Use `continuity_start_mode: previous_final_frame` when the same scene continues. Use `storyboard_image` when location, time, or composition changes.

At this point, `storyboard.json` is machine input, not the official user-review storyboard. Do not proceed to video generation from JSON or Markdown alone.

## 6. Review starting images and build the Excel storyboard

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001 --limit 1
```

Review the first image for 16:9 framing, every character's appearance, left-right placement, props, background, unintended text or logos, and subtitle space. Do not generate video from an incorrect starting image.

After the first image passes, remove `--limit` and generate the remaining shots. When every main image exists, the application automatically creates the official `review/storyboard_v001.xlsx` workbook plus Japanese and English local HTML review pages. An explicit rebuild creates `_r002`, `_r003`, and later revisions instead of overwriting a reviewed file:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-workbook `
  --run-dir output\storyboard\v001
```

Every shot sheet contains the main image, visible action, emotion, camera, lighting, dialogue, sound, continuity, nine-frame plan, review status, and a yellow correction field. The application refuses to build the official workbook until all main images exist.
A rebuilt revision starts at `未確認`. Even when an older approved file remains, the newest changed image or plan must always be reviewed again.

## 7. Review, correct, and approve the Excel storyboard

The Excel workbook is the official human-review artifact. A path or chat link alone is not a handoff. The AI agent opens the containing folder, selects the artifact, gives one opening action, and stops here:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact storyboard --language en
```

When Excel, LibreOffice Calc, or Numbers is available, this selects the workbook. Otherwise it selects the generated English local HTML review page. The HTML page stays offline and stores review entries in the browser; the workbook beside it remains the official record. The first instruction is only: “Double-click the selected file. When it opens, reply: Opened.” After that reply, guide the workbook tabs, status, yellow correction field, and saving one action at a time. In HTML, the user reviews each card and pastes the generated summary into chat.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py extract-corrections `
  --workbook output\storyboard\v001\review\storyboard_v001.xlsx
```

The agent applies corrections to the JSON and starting images, rebuilds the workbook, and requests another review. Only after the user explicitly approves the workbook may the agent run:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py approve-workbook `
  --run-dir output\storyboard\v001
```

`approve-workbook` lets an agent mark unreviewed sheets approved only after the user explicitly approves the workbook. It fails if any sheet is marked for revision or contains an unapplied correction. `render-videos` refuses to run until every sheet in the Excel storyboard is approved. An agent must not infer approval from silence, file existence, or approval of an older version.

If an open spreadsheet application locks the workbook, ask the user to save and close it, then wait for their reply before retrying. In a remote or headless environment, never claim a folder opened; report the exact folder and filename and give one manual action.

## 8. Generate three-second clips

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-videos `
  --run-dir output\storyboard\v001
```

Each shot fixes the approved identity image, neutral presence, activated signature motion, and prohibited changes. If the selected model cannot accept the reference MP4 directly, send keyframes around 0.25, 1.50, and 2.75 seconds together with the timed three-second motion description.

Within the same scene, extract the previous clip's final frame and use it as the next starting frame. Extract nine frames from every generated shot and check duplication, part count, color, pose, framing, and the three-second boundary.

## 9. Finish voices, music, sound, and subtitles

Do not use audio generated incidentally by the video API. Keep only the video stream.

- Dialogue and narration: generate with controlled TTS, then review duration and pronunciation.
- Ambience and effects: use clearly licensed assets or deterministic local synthesis.
- Music: record provenance and rights, and mix it below dialogue.
- Japanese or English captions: render locally with ASS or a comparable format and machine-check required text.

For multiple speakers, store each shot's `voice`, `speaker`, and `style` in JSON and pass it through `--voice-config`. Design ambience across the entire finished timeline, not as isolated three-second loops. Preserve tails between shots, increase sound as the camera approaches a source, pan with screen motion, duck under dialogue, and leave intentional quiet after an impact or landing.

The existence of an audio stream is not a quality pass. Listen from beginning to end for perceptible silence, mismatched mouth motion and dialogue, environmental changes without corresponding sound changes, and abrupt cuts. Record full-program LUFS and true peak as well as average and maximum level, waveform, and spectrogram for each three-second interval.

```powershell
.\.venv\Scripts\python.exe scripts\generate_storyboard_tts.py `
  --run-dir output\storyboard\v001 `
  --voice-config examples\space-friends\tts_config.json

.\.venv\Scripts\python.exe scripts\rebuild_clean_soundtrack.py `
  --run-dir output\storyboard\v001 `
  --ambience-profile space-to-nature
```

For a production-specific cinematic mix, synthesize it locally with a tool such as `build_cinematic_soundtrack.py`. Assemble the captioned picture first, then explicitly mux only the approved picture and audio streams so that no video-model audio survives.

```powershell
.\.venv\Scripts\python.exe scripts\build_cinematic_soundtrack.py `
  --run-dir output\space-friends\v002 `
  --input-video output\space-friends\v002\final\story_video_v002.mp4 `
  --output-video output\space-friends\v002\final\story_video_v002_cinematic.mp4
```

Transcribe TTS with a different speech-recognition model and compare it with the script after normalizing punctuation and orthographic variants. Transcribe the finished mix again to verify that dialogue remains intelligible after ambience and music are added. Also inspect an audio-only transcript for missing lines, cross-talk, or unintended generated speech.

## 10. Assemble and perform final review

```powershell
.\.venv\Scripts\python.exe run_storyboard.py finalize-video `
  --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook `
  --run-dir output\storyboard\v001
```

Use the same folder-and-one-action handoff for the generated-video review, final MP4, and AI model-use record:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact video-review --language en
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact final-video --language en
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact ai-record --language en
```

A human watches the entire video and reviews picture, speech, captions, payoff, duration, and rights notices. In particular, check that a silent character's mouth or service seams do not move, a flying character's head, neck, and torso point consistently, and environmental audio matches on-screen distance and position. Never overwrite an approved version; create `v002` or another new version. Move rejected material into the run's `rejected` directory with a name that records the reason.

## 11. Always keep an AI model-use record

For every episode, copy `templates/AIモデル使用記録.md` to `final/AIモデル使用記録.md` under the completed run. Mark unused stages as `Not used` rather than omitting them.

At minimum, record these stages separately:

- concept, script, and storyboard
- character appearance design
- character-design videos
- starting images
- three-second videos, separated by shot ranges
- TTS and narration
- music, ambience, and effects
- overall sound design, dialogue timing, LUFS, true peak, and interval levels
- captions, assembly, color, and level adjustments
- transcription and quality assurance
- final human decisions

Record provider, model name, function, input, output, accepted range, regeneration reason, local processing, and date. If the video model changes between shots, split the ranges.

## 12. Pre-publication inspection

- No `.env`, key, email address, personal path, or client identifier
- No production content from local `input` or `output` in Git
- No real person, client, family member, pet, or previous work in the public sample
- Publication basis and license recorded for every asset
- No provider operation identifier or private provider metadata
- Offline tests pass without API credentials
- Every staged file reviewed with `git diff --cached`
