English | [日本語](README.ja.md)

# nijiunit-public-ai-agent-video-studio

A public reference implementation for producing short, three-second AI video clips with AI agents while keeping character appearance and motion as consistent as possible.

This repository is the trusted local runtime. It contains basic operation, bundled production defaults, safety checks, and human approval gates. The NijiUnit website contains only the guide for recreating each published NijiUnit video; the AI agent reads that page directly each time. Work-specific characters, dialogue, and endings remain in the user's production data.

The central problem addressed by this repository is continuity across shots, not merely generating isolated clips.

- A versioned character registry for appearance, prohibited changes, and asset rights
- Newly generated three-second character-design videos for neutral presence and signature motions
- Timestamped keyframes and motion instructions extracted from those design videos
- Continuous generation that passes the final frame of one clip into the next compatible shot
- A mandatory Excel storyboard containing every main image, shot plan, audio plan, nine-frame plan, and correction field; offline local HTML review for users without a spreadsheet app; and a hard approval gate before video generation
- Nine-frame visual review of every generated clip, followed by local audio and subtitle finishing
- An episode-level record of every AI model used

A small public finished video, approved Excel storyboard, and Japanese/English HTML review pages are bundled under `examples/space-friends/`. Complete HOWTO production sources and work-specific reproduction code remain in the separate `nijiunit-public-ai-agent-video-studio-howto-movie` repository.

## What the public repository excludes

This is not a direct publication of the private production repository. It excludes real people, family members, pets, non-public previous productions, client-specific scripts, private production history, API keys, and private provider metadata. The bundled sample is a fictional public production only.

## Ask an AI agent

Open the cloned repository in Codex or another compatible AI agent and ask:

```text
Please make this application ready to use.
```

Codex starts from [AGENTS.md](AGENTS.md), Claude Code from [CLAUDE.md](CLAUDE.md), and Google Antigravity from its automatically loaded [.agents/rules/nijiunit.md](.agents/rules/nijiunit.md), which points to [GEMINI.md](GEMINI.md). Each route then reads the same English detailed guide. The agent runs the dedicated setup script and checks the virtual environment, dependencies, bundled production defaults, `.env`, and FFmpeg. If an API key is missing, it opens an illustrated local setup page for Google AI Studio, masked secret entry, and connection verification. A beginner does not normally paste the key into a terminal. Setup never calls a generation API and never overwrites an existing `.env` without permission.

This request assumes that the upstream guide has already helped the user install an AI agent and Git, clone the repository, and open this folder. From that point, this repository is responsible for Python, FFmpeg, Google Generative AI API pricing and billing guidance, secure API-key setup, and connection checks. A greeting alone routes directly to the tutorial-or-from-scratch choice. The agent asks only for meaningful decisions and does not stop on progress-only messages; routine actions that form one review task stay together.

To receive an explanation without installing or changing anything, ask:

```text
Please explain how to use this application.
```

The agent uses the [English getting-started guide](docs/getting-started.md) and explains the workflow without installing packages or calling an API.

## Setup responsibility

Python 3.11 or later is required. If Python is missing, the AI agent follows the [first-time Python setup guide](docs/python-setup.md).

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

macOS / Linux:

```bash
bash scripts/setup.sh
```

Manual Windows setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "."
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe scripts\doctor.py
```

After local setup, the agent follows the [first-time Google Generative AI API guide](docs/google-api-setup.md) only when no key is configured. If setup is already complete and unchanged, it does not open the page or ask to repeat setup. The user must verify the paid-access requirement, current prices, selected project, and billing terms for every configured model before production use.

When obtaining or replacing a key, do not paste it into chat. The agent opens the dedicated local browser page, and the user pastes the key into its masked field.

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\open_setup.py --language en
```

macOS / Linux:

```bash
./.venv/bin/python scripts/open_setup.py --language en
```

The page listens only on this computer's `127.0.0.1` address and stores the key only in the Git-ignored `.env`. It does not put the key in chat, a URL, logs, or browser storage. Its connection check generates no media: it checks authentication and confirms that the configured story, image, video, TTS, and speech-review model identifiers appear in the provider model catalog. It does not guarantee paid generation, account balance, regional availability, or quota. Before the first generation request, the agent explains that charges may apply and waits for the user's request. `scripts/configure_api_key.py` and the command-line doctor remain recovery tools for environments where the browser page cannot run.

## First local check

Check the local environment and available commands without calling a generation API.

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
.\.venv\Scripts\python.exe run_storyboard.py --help
```

## Create your own video

1. Choose horizontal `16:9` for a regular YouTube video or vertical `9:16` for a YouTube Short.
2. Put `story.md` and rights-cleared source material in `input`.
3. Use `templates` to create a versioned character registry under `characters`.
4. Validate the registry, design videos, and keyframes.
5. Create the three-second plan and starting images, then build the official Excel storyboard.
6. The agent opens the review folder and selects either the workbook or local HTML page. Review every shot and apply corrections. Video generation is blocked until the user explicitly approves it.
7. Generate three-second clips from the approved workbook and inspect nine real frames from every clip.
8. Discard generated audio, add controlled voices and subtitles locally, and save the final MP4 and AI model-use record.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create --aspect-ratio 9:16
.\.venv\Scripts\python.exe run_storyboard.py render-images --run-dir output\storyboard\v001
# Open the folder and select Excel, or English local HTML if no spreadsheet app exists.
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact --run-dir output\storyboard\v001 --artifact storyboard --language en
# Run this only after the user explicitly approves the storyboard.
.\.venv\Scripts\python.exe run_storyboard.py approve-workbook --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py render-videos --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py finalize-video --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook --run-dir output\storyboard\v001
```

See the detailed [production workflow](WORKFLOW.md).

## Learn from a nijiunit YouTube video

When you ask to create something based on a NijiUnit video, the AI agent asks for one YouTube URL. It extracts the video ID, opens the corresponding language-matched guide on the configured NijiUnit website, validates the page contract, reads the linked documents directly, and then explains one action at a time.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://www.youtube.com/watch?v=VIDEO_ID" --language en
```

Normal preparation does not call a generation API and does not reanalyse the YouTube video. The website guide is the official lesson. The downloaded page and Markdown are reference text only: they never override local safety rules or become executable code.

## Updates

NijiUnit activity and new-video announcements are published on YouTube. Source-code updates are checked against GitHub only when requested; the agent reports the result and asks before changing the local checkout.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update
```

The command never updates files by itself. Local edits and uncommitted work must be protected before any pull or release change.

## Repository layout

```text
characters/  Reusable local character registry; initially documentation only
config/      Bundled production defaults and public-site/GitHub endpoints
docs/        Architecture, model selection, setup, and safety documentation
examples/    A complete, publishable sample
input/       Current local input; contents are ignored by Git
output/      Generated output; contents are ignored by Git
scripts/     Validation, review-sheet, and finishing helpers
src/         Shared implementation
templates/   Character-registry and AI-use-record templates
tests/       Offline automated tests
```

Older production runs may contain a pinned remote-guidance snapshot for audit compatibility. New runs use the SHA-256-verified production defaults committed under `config/runtime-guidance/` and do not depend on a daily website cache.

Codex uses the root `AGENTS.md`, Claude Code uses `CLAUDE.md`, and Google Antigravity loads `.agents/rules/nijiunit.md` before following it to `GEMINI.md`. Detailed common setup, usage, production, and release rules live in `docs/agent-guide.md`.

There is no permanent `temp` directory. Use the Git-ignored `tmp/` for temporary data. Public `input` and `output` contain only documentation or placeholders; user content remains local.

Within a production run, user review workbooks and HTML pages live in `review/`, finished MP4s and final records in `final/`, and rejected material in `rejected/`. After processing, the agent opens the relevant folder, selects the artifact, and gives the complete current review task without extra opening acknowledgements.

Versions apply to the whole production run, not an individual workbook. The first run is `v001`; any reviewed storyboard, image, video, or audio correction creates `v002` or later while keeping the prior run unchanged. Filenames stay aligned as `storyboard_vNNN.xlsx`, `story_video_vNNN.mp4`, and `storyboard_vNNN_video.xlsx`. Legacy `_r002` workbooks remain readable but are not created for new work.

## Important limitations

- Character-design MP4s are retained, but if a video model cannot reliably accept multiple video references, the workflow sends three keyframes and timed motion instructions instead of the MP4 itself.
- `previous_final_frame` is used only between shots in the same scene. A new starting image is used when location, time, or composition changes.
- Generative output remains nondeterministic. Registries, continuity frames, and review gates reduce drift but cannot guarantee exact identity.
- The Excel storyboard is the official human-review artifact. `storyboard.json` and Markdown files cannot replace its approval gate.
- Users without Excel, LibreOffice Calc, or Numbers can inspect the same content in an offline local HTML page. HTML review does not bypass explicit approval or the official Excel gate.
- Generated speech and text inside video are not trusted as final assets. Required dialogue and subtitles are produced and checked separately.
- This code does not grant rights to publish someone else's face, character, music, or logo.

## License

Code and documentation are available under the [MIT License](LICENSE). Public demo media is governed by [ASSET_LICENSES.md](ASSET_LICENSES.md).

## Development and releases

`project.version` in `pyproject.toml` is the single version source. Ordinary changes are recorded under `Unreleased` in `CHANGELOG.md`; the version changes only during explicit release preparation. See the [release guide](docs/releasing.md).
