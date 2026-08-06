English | [日本語](README.ja.md)

# nijiunit-public-ai-agent-video-studio

A public reference implementation for producing short, three-second AI video clips with AI agents while keeping character appearance and motion as consistent as possible.

The central problem addressed by this repository is continuity across shots, not merely generating isolated clips.

- A versioned character registry for appearance, prohibited changes, and asset rights
- Newly generated three-second character-design videos for neutral presence and signature motions
- Timestamped keyframes and motion instructions extracted from those design videos
- Continuous generation that passes the final frame of one clip into the next compatible shot
- Nine-frame visual review of every generated clip, followed by local audio and subtitle finishing
- An episode-level record of every AI model used

![Mio and Lux fly beside the rainbow waterfall](examples/space-friends/assets/shot_008_start_v002.png)

[▶ Open the completed 30-second demo, "The Rainbow Beyond the Stars"](examples/space-friends/demo.mp4)

The public demo includes shot-specific starting images; dedicated motions for space flight, a cinematic descent, a waterfall pass, low-altitude flight, and landing; shot-specific TTS; and a continuous local soundtrack that moves from space ambience to wind, river, waterfall, and grassland. Its storyboard, character registry, AI model-use record, and 90-frame review sheet are all under [examples/space-friends](examples/space-friends).

## What the public repository excludes

This is not a direct publication of the private production repository. It excludes real people, family members, pets, previous productions, client-specific scripts, private production history, API keys, and private provider metadata. The sample contains only Mio and Lux, fictional characters created for public use.

## Ask an AI agent

Open the cloned repository in Codex or another compatible AI agent and ask:

```text
Please make this application ready to use.
```

Following [AGENTS.md](AGENTS.md), the agent runs the dedicated setup script and checks the virtual environment, dependencies, `.env`, FFmpeg, and public sample. If an API key is missing, it guides the user through Google AI Studio, hidden local input, and a new diagnostic. Setup never calls a generation API and never overwrites an existing `.env` without permission.

This request assumes that the upstream guide has already helped the user install an AI agent and Git, clone the repository, and open this folder. From that point, this repository is responsible for Python, FFmpeg, Google Generative AI API pricing and billing guidance, secure API-key setup, and connection checks. When a beginner must operate a screen, the agent explains only one action at a time.

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

After local setup, the agent follows the [first-time Google Generative AI API guide](docs/google-api-setup.md), one user action at a time. The default video model requires paid access, so the user must review current prices, the selected project, and billing terms before creating an API key for production use.

After obtaining a key, do not paste it into chat. Enter it into the dedicated local tool; the input is hidden.

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\configure_api_key.py
.\.venv\Scripts\python.exe scripts\doctor.py --require-api-key --verify-api-key-online
```

macOS / Linux:

```bash
./.venv/bin/python scripts/configure_api_key.py
./.venv/bin/python scripts/doctor.py --require-api-key --verify-api-key-online
```

The key is stored only in the Git-ignored `.env`. The online diagnostic generates no media: it checks authentication and confirms that the configured story, image, video, and TTS model identifiers appear in the provider model catalog. It does not guarantee paid generation, account balance, regional availability, or quota. Before the first generation request, the agent explains that charges may apply and waits for the user's request.

## Try the public sample

The registry and motion references can be validated without any API call.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py validate-characters `
  --registry-dir examples\space-friends\characters

.\.venv\Scripts\python.exe scripts\validate_character_design_videos.py `
  --registry-dir examples\space-friends\characters
```

The complete public sample is in [examples/space-friends](examples/space-friends).

## Create your own video

1. Put `story.md` and rights-cleared source material in `input`.
2. Use `templates` to create a versioned character registry under `characters`.
3. Validate the registry, design videos, and keyframes.
4. Generate the three-second storyboard, starting images, and video clips in that order.
5. Inspect nine real frames from every clip, discard generated audio, and add controlled voices and subtitles locally.
6. Save the final MP4 and the episode's AI model-use record.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create
.\.venv\Scripts\python.exe run_storyboard.py render-images --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-workbook --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py render-videos --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py finalize-video --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook --run-dir output\storyboard\v001
```

See the detailed [production workflow](WORKFLOW.md).

## Repository layout

```text
characters/  Reusable local character registry; initially documentation only
docs/        Architecture, model selection, setup, and safety documentation
examples/    A complete, publishable sample
input/       Current local input; contents are ignored by Git
output/      Generated output; contents are ignored by Git
scripts/     Validation, review-sheet, and finishing helpers
src/         Shared implementation
templates/   Character-registry and AI-use-record templates
tests/       Offline automated tests
```

The root `AGENTS.md` tells AI agents how to route setup, usage, production, and release requests in the user's selected language.

There is no permanent `temp` directory. Use the Git-ignored `tmp/` for temporary data. Public `input` and `output` contain only documentation or placeholders; user content remains local.

## Important limitations

- Character-design MP4s are retained, but if a video model cannot reliably accept multiple video references, the workflow sends three keyframes and timed motion instructions instead of the MP4 itself.
- `previous_final_frame` is used only between shots in the same scene. A new starting image is used when location, time, or composition changes.
- Generative output remains nondeterministic. Registries, continuity frames, and review gates reduce drift but cannot guarantee exact identity.
- Generated speech and text inside video are not trusted as final assets. Required dialogue and subtitles are produced and checked separately.
- This code does not grant rights to publish someone else's face, character, music, or logo.

## License

Code and documentation are available under the [MIT License](LICENSE). Public demo media is governed by [ASSET_LICENSES.md](ASSET_LICENSES.md).

## Development and releases

`project.version` in `pyproject.toml` is the single version source. Ordinary changes are recorded under `Unreleased` in `CHANGELOG.md`; the version changes only during explicit release preparation. See the [release guide](docs/releasing.md).
