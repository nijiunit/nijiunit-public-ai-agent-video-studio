English | [日本語](agent-guide.ja.md)

# Working instructions for AI agents

This repository implements the public "NIJIUNIT Video Generation Tool." It takes over after an upstream guide has installed the AI agent and Git, cloned the repository, and opened this folder. Its responsibilities are preparing Python, FFmpeg, and the Google Generative AI API, then operating the three-second video-production workflow.

## Read first

Read the material relevant to the request:

1. `README.md`
2. `docs/getting-started.md`
3. For video production or implementation changes, `WORKFLOW.md`

Production starts in `input`. The complete public sample is `examples/space-friends`.

## Route the request

### Setup requests such as "Please make this application ready to use"

Assume the user may be a computer beginner. Do not reinstall the AI agent or Git and do not clone the repository again. Start from the already opened repository.

#### Interaction rules

- Run diagnostics that the AI agent can perform safely.
- When the user must act, explain only one operation per response.
- Wait for confirmation such as "Done" before continuing to the next screen.
- If a screen differs from expectations, ask for a non-secret heading or button label. Do not make the user guess.
- Explain and obtain confirmation before installing system software or changing a contract, billing, or automatic payments.
- Never ask for a password, card number, verification code, or API key in chat, logs, screen sharing, or command arguments.

#### A. Prepare the OS and Python

1. Detect the operating system.
2. On Windows, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
   ```

3. On macOS or Linux, run:

   ```bash
   bash scripts/setup.sh
   ```

4. If setup reports missing Python with `ACTION_REQUIRED`, follow [first-time Python setup](python-setup.md) one user action at a time. Use Windows `-InstallPython` only after user confirmation.
5. Run setup again and resolve every local `FAIL`.
6. When the result is `LOCAL READY (Google API setup required)`, report that only local setup is complete. Do not claim the entire application is ready.

#### B. Prepare the Google Generative AI API

1. Read the complete [Google API setup guide](google-api-setup.md).
2. Guide account access, terms, project selection, current pricing, paid access, and billing one user action at a time. Explain before billing setup that the default video model requires paid access.
3. If the user declines billing, stop and report: "The public demo and local tools are available; Google video generation is not configured."
4. If the user proceeds, they enter payment information directly into Google. Never choose card details, automatic top-up, Prepay, or Postpay for them.
5. Ask the user to confirm the intended project's paid status and, when applicable, usable Prepay balance on the live screen.
6. After the user obtains an API key, have them run `configure_api_key.py` in their own interactive local terminal. Never request the key itself.
7. After storage, run `doctor.py --require-api-key --verify-api-key-online`.
8. If the result is `READY FOR GENERATION (paid generation not tested)`, report accurately that authentication and model identifiers were verified but paid generation was not attempted.
9. Before the first image or video generation, explain that charges may apply and wait for a user request. Never run a paid test without that request.

Setup must not call story, image, video, speech, or music generation. It must not overwrite an existing `.env`. The key tool changes an existing key only when `--replace` is explicit.

### Explanation requests such as "Please explain how to use this application"

Use `docs/getting-started.md` as the source and explain in English at the user's level. An explanation-only request does not authorize package installation, API calls, or file changes.

Begin with this short overview:

1. Prepare Python and the local environment.
2. Review Google API pricing and billing, then store the API key safely.
3. Write the story in `input/story.md`.
4. Create the official Excel storyboard from the three-second structure and starting images.
5. Have the user review, correct, and explicitly approve the Excel workbook.
6. After approval, generate three-second clips and inspect nine frames from every clip.
7. Finish voices, subtitles, and sound, then inspect the final video.

Then focus only on the user's goal: creating a new video, reviewing the public demo, or registering a character.

### Video-production requests

Read `WORKFLOW.md` and start from `input`. After all starting images exist, create the official Excel storyboard and stop before video generation until explicit approval. JSON and Markdown do not replace the workbook. Build a new workbook revision after corrections and run `approve-workbook` only after approval. Treat the active, versioned character registry as authoritative. Continue compatible scenes from the previous clip's final frame. Inspect every generated clip in nine frames and move rejected assets to `rejected` with a recorded reason.

#### Required beginner artifact handoff

- Do not stop after printing a path or chat link. Open the containing folder and select the actual artifact.
- Use `run_storyboard.py reveal-artifact` for a production run and `scripts/reveal_artifact.py --path ...` for another exact file.
- Detect Excel, LibreOffice Calc, or Numbers. If none is installed, select the generated English local HTML review page. Do not require an Excel purchase solely for review.
- After the folder opens, give exactly one action: “Double-click the selected file. When it opens, reply: Opened.” Wait before explaining sheet tabs, correction fields, saving, or the next stage.
- In a remote or headless session, do not claim the folder opened. Give the exact folder, filename, and one manual action.
- Never overwrite a reviewed workbook. Use `_r002`, `_r003`, and later revisions. If the workbook is locked, ask the user to save and close it, then wait for their reply.
- After the workbook opens, guide the first sheet, tabs, status, yellow correction field, and saving one action at a time. With HTML, have the user review each card and paste the generated summary into chat.
- Repeat this handoff for the generated-video review, final MP4, and AI model-use record. Lead completion reports with the artifact the user can now inspect, not implementation details or test counts.

For example, this command selects the workbook, or the local HTML page when no spreadsheet application is available:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact storyboard --language en
```

Before calling an API, confirm that `.env` contains a key without displaying its value. Do not call an API for diagnosis or explanation when the user did not request generation.

### Repository maintenance and release requests

`project.version` in `pyproject.toml` is the single version source. Do not create a separate `VERSION` file. Follow `docs/releasing.md`.

- Do not change the version during ordinary implementation or documentation work.
- Record user-visible features, fixes, and security changes under `Unreleased` in `CHANGELOG.md`. Typographical, formatting, internal-test, and no-user-impact changes normally need no entry.
- Only an explicit release-preparation request authorizes changing `project.version` and creating the matching dated CHANGELOG heading.
- Use PATCH for backward-compatible fixes, MINOR for backward-compatible features, and MAJOR for incompatible changes. Confirm ambiguous pre-1.0 incompatible changes with the user.
- Before release, run `python scripts/check_release_version.py`, `pytest`, `ruff check .`, and `python scripts/check_public_repo.py`.
- Commit, push, tag creation, GitHub Release creation, and visibility changes each require explicit user authorization.
- Never move a published version or tag. Publish a new PATCH release for corrections.

## Safety and publication quality

- Never add `.env`, API keys, personal information, or private media to Git.
- Never mix real people, clients, family, pets, or private characters into the public sample.
- Preserve existing files and user changes.
- Prefer the repository setup scripts over ad hoc global installation.
- Do not accept generated speech or on-screen text without verification.
- After implementation changes, run at least `pytest`, `ruff check .`, and `scripts/check_public_repo.py`.

## Diagnostic command

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

macOS or Linux:

```bash
./.venv/bin/python scripts/doctor.py
```

`LOCAL READY` covers only local components. `READY FOR GENERATION (paid generation not tested)` covers authentication and the model catalog, not a successful paid generation. If any check is `FAIL`, do not report the application as ready.
