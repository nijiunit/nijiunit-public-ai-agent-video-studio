English | [日本語](getting-started.ja.md)

# Getting started with AI Agent Video Studio

This command-line application turns a story and character references into three-second video clips, then supports assembly, voices, subtitles, sound, and final review. It is designed to be operated through natural-language requests to an AI agent rather than through a browser interface.

## Requests you can give an AI agent

After cloning the repository and opening it in an AI agent, ask:

```text
Please make this application ready to use.
```

Following `AGENTS.md`, the agent prepares and diagnoses Python, the virtual environment, dependencies, the `.env` template, FFmpeg, and the public sample. It then guides you through Google Generative AI API prices, billing, API-key storage, and connection verification one action at a time. Installation does not call a generation API.

For an explanation only, ask:

```text
Please explain how to use this application.
```

For a new production, requests can be as specific as:

```text
Review the story and images in input and create a three-second storyboard.
Generate only the first starting image, then stop for my review.
Build the Excel storyboard with every starting image and stop for my approval.
After approval, generate three-second shots and inspect each one as nine frames.
```

## 1. Prepare the local environment

If you are setting up manually rather than through an AI agent, run the platform script.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

macOS or Linux:

```bash
bash scripts/setup.sh
```

Examples in this guide primarily use PowerShell. On macOS or Linux, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python` and use `/` as the path separator.

The script requires Python 3.11 or later, creates `.venv`, and installs this project in editable mode. If Python is unavailable, it stops with `ACTION_REQUIRED`. The AI agent then follows the [first-time Python setup guide](python-setup.md) and obtains permission before installing software.

If `.env` is missing, setup copies `.env.example`. It never overwrites an existing `.env`.

Diagnostic states have precise meanings:

- `LOCAL READY (Google API setup required)`: local setup is complete; Google API is not configured
- `LOCAL READY (online verification required)`: an API key is stored; online verification is still required
- `READY FOR GENERATION (paid generation not tested)`: authentication and configured model identifiers were verified; no paid generation was attempted
- `NOT READY`: at least one problem must be resolved

A `WARN` for `spreadsheet viewer` is not a setup failure because offline local HTML review is available. The user can continue without installing Excel, LibreOffice Calc, or Numbers.

## 2. Prepare the Google Generative AI API

This first-time process follows the [Google API setup guide](google-api-setup.md). The AI agent must guide the user one action at a time rather than presenting all screens at once.

### 2.1 Review pricing before creating production resources

The default video model, `gemini-omni-flash-preview`, requires paid access. In Google AI Studio, the user personally reviews the terms, current pricing, selected project, Prepay or Postpay terms, deposits, and automatic top-up behavior.

The AI agent does not choose a payment method or automatic top-up. If the user declines paid setup, the public demo and offline tools remain available.

Use the official [Gemini API billing guide](https://ai.google.dev/gemini-api/docs/billing) and [current pricing page](https://ai.google.dev/gemini-api/docs/pricing).

### 2.2 Obtain an API key in Google AI Studio

Open [Google AI Studio API Keys](https://aistudio.google.com/app/apikey) and confirm that the intended project has the appropriate plan or billing tier. Reuse a suitable existing key instead of creating duplicates.

Treat the key like a password. Never paste it into chat, an issue, email, screen sharing, a command argument, or a committed file. If it is exposed, revoke it in Google AI Studio and create a replacement.

### 2.3 Store the key without displaying it

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\configure_api_key.py
```

macOS or Linux:

```bash
./.venv/bin/python scripts/configure_api_key.py
```

Paste the key at the prompt and press Enter. Hidden input is expected. The tool preserves other `.env` settings and never prints the key. To replace an existing key, explicitly add `--replace`.

```powershell
.\.venv\Scripts\python.exe scripts\configure_api_key.py --replace
```

The Git-ignored `.env` is the only local file intended to store this key.

### 2.4 Verify authentication and configured models

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py --require-api-key --verify-api-key-online
```

macOS or Linux:

```bash
./.venv/bin/python scripts/doctor.py --require-api-key --verify-api-key-online
```

This diagnostic does not generate media. It checks Google authentication and verifies that the configured story, image, video, and TTS model identifiers appear in the model catalog. It does not guarantee account balance, quota, regional access, preview eligibility, or a successful paid generation. Confirm possible charges before the first user-approved generation.

## 3. Review the public demo

The completed example is under `examples/space-friends`.

- Final video: `examples/space-friends/demo.mp4`
- Story: `examples/space-friends/input/story.md`
- Approved Excel storyboard: `examples/space-friends/storyboard_approved.xlsx`
- Offline Japanese and English storyboard pages: `storyboard_approved_review.ja.html`, `storyboard_approved_review.en.html`
- Machine-readable three-second plan: `examples/space-friends/storyboard.json`
- Character registry: `examples/space-friends/characters`
- AI model-use record: `examples/space-friends/AIモデル使用記録.md`
- 90-frame review sheet: `examples/space-friends/docs/story-video-contact-sheet.jpg`

For a beginner, do not stop at these path labels. Have the AI agent reveal the exact file in its folder. For the Excel storyboard:

```powershell
.\.venv\Scripts\python.exe scripts\reveal_artifact.py `
  --path examples\space-friends\storyboard_approved.xlsx --language en
```

Ask the user to double-click the selected file and wait for “Opened” before giving the next instruction.

Validate the registry and motion videos without an API call:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py validate-characters `
  --registry-dir examples\space-friends\characters

.\.venv\Scripts\python.exe scripts\validate_character_design_videos.py `
  --registry-dir examples\space-friends\characters
```

## 4. Enter a new story

Create `input/story.md` and describe:

- the characters and their goal
- the events and ending
- exact dialogue and speaker assignments
- desired visual style and aspect ratio
- appearance, background, and prop details that must not change
- exact text that must appear on screen

You may copy the public story as a starting point:

```powershell
Copy-Item examples\space-friends\input\story.md input\story.md
```

For every reference image or video placed in `input`, record its source and usage rights.

## 5. Create the three-second storyboard

The following command calls a generation API:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create
```

It creates a new run such as `output/storyboard/v001` and prints the actual path. Use that path for later `--run-dir` arguments.

To explicitly use the public sample registry as a reference:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create `
  --character-registry-dir examples\space-friends\characters
```

## 6. Review starting images and build the Excel storyboard

Do not generate every image immediately. Review the first one:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001 --limit 1
```

Check identity, character count, left-right placement, background, unintended text or logos, 16:9 framing, and subtitle space. Remove `--limit` only after approval.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001
```

When every shot's starting image exists, the application automatically creates `output/storyboard/v001/review/storyboard_v001.xlsx` plus Japanese and English local HTML review pages. The workbook is the official storyboard. JSON and Markdown are machine input and supplementary documentation; they do not replace the workbook. A corrected build keeps the old workbook and creates `_r002`, `_r003`, and later revisions.

## 7. Review and approve the Excel storyboard

First, the AI agent runs:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact storyboard --language en
```

On macOS or Linux, start the same command with `./.venv/bin/python run_storyboard.py`. Finder selects the target file. If the Linux file manager cannot select it, use the exact filename printed for the already-open folder.

This selects the workbook when Excel, LibreOffice Calc, or Numbers is available; otherwise it selects the English local HTML page in the same `review` folder. The agent gives only one action: “Double-click the selected file. When it opens, reply: Opened.”

After the workbook opens, review every sheet's main image, description, dialogue, sound, action, and nine-frame plan. For a correction, set `レビュー状態` to `修正必要`, write the exact request in the yellow correction field, and save. In HTML, review each card and paste the generated summary into chat. The AI agent applies corrections and creates a new workbook revision for another review.

Only after the user explicitly approves the workbook may the agent run:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py approve-workbook `
  --run-dir output\storyboard\v001
```

The application blocks video generation before user approval.

If the workbook is locked because it is still open, the agent asks for one action—save and close it—and waits for the reply. In a headless or remote environment, the agent reports the exact folder and filename instead of claiming that a desktop folder opened.

## 8. Generate and inspect three-second clips

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-videos `
  --run-dir output\storyboard\v001 --limit 1
```

Review the first clip before generating the rest. Each clip is extracted into nine frames; inspect faces, colors, part counts, necks, hands, feet, backgrounds, framing, and continuity.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook `
  --run-dir output\storyboard\v001
```

Reveal the generated-video review in the same way. Without a spreadsheet app, the command selects local HTML containing the nine real frames from every clip.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact video-review --language en
```

## 9. Assemble and finish

```powershell
.\.venv\Scripts\python.exe run_storyboard.py finalize-video `
  --run-dir output\storyboard\v001
```

The final video is written below the run's `final` directory. Keep dialogue, subtitles, ambience, music, and level control separate from video generation. Do not accept accidental generated speech or on-screen text as a final asset. See the detailed [production workflow](../WORKFLOW.md).

At completion, the agent uses `--artifact final-video` to open the `final` folder and select the MP4, then gives one action: double-click it and watch from beginning to end.

## 10. Add a reusable character

Use `templates/character-profile.json` and `templates/character-registry.json` to build a versioned registry under `characters/<id>/<version>`.

Each reusable character needs:

- an approved identity image
- fixed face, body, color, clothing, and material details
- prohibited parts and motions
- a newly generated three-second neutral-presence design video
- design videos for required signature motions
- publication status, provenance, and asset license

See `character-registry.md` and the [production workflow](../WORKFLOW.md).

## 11. Troubleshooting

Run the local diagnostic first:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

See `troubleshooting.md` for common problems. Provider models, availability, and prices can change, so verify current official information before paid generation.
