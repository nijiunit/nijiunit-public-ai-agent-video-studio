# Troubleshooting

## Setup finishes with `LOCAL READY (Google API setup required)`

The base application and local video tools are installed, but generation is not
ready yet. Follow `docs/google-api-setup.md` one user action at a time. Because
the default video model is paid-tier, confirm pricing, the project billing plan,
and any prepaid balance before creating or reusing a key. Never paste the key
into chat. Setup itself does not call a generation API.

## Google AI Studio does not show `Create API key`

Confirm that you are signed into the intended Google account and review any
terms, region, age, organization, or Google Cloud project messages shown on the
page. Do not send the API key itself when asking for help. See the official
[Gemini API-key guide](https://ai.google.dev/gemini-api/docs/api-key) and
[Google AI Studio troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshoot-ai-studio).

## The API key was pasted into chat or committed to Git

Treat it as exposed. Revoke the key in Google AI Studio, create a replacement,
and run `scripts/configure_api_key.py --replace`. Removing a key from the latest
file is not enough if it remains in chat, logs, or Git history.

## Setup reports that Python is missing or too old

Follow `docs/python-setup.md`. On Windows, the agent may rerun `setup.ps1` with
`-InstallPython` only after the user agrees. On macOS, use the signed installer
from python.org and complete the certificate step. Reopen the terminal and rerun
setup. Existing `.venv` and `.env` files are preserved.

## Authentication passes but a configured model is missing

Confirm that `.env` contains current model identifiers and that the key belongs
to the intended paid project. Preview model availability can depend on region,
account, and rollout. Check the official model and pricing pages before changing
the model. Do not silently substitute a model because quality and pricing differ.

## Doctor says paid generation was not tested

This is expected. The online diagnostic reads provider metadata but does not
create paid media. Before the first image or video request, tell the user that
charges may occur and wait for an explicit generation request. A successful
first generation is the final proof of billing, quota, region, and model access.

## `doctor.py` reports an FFmpeg failure

Rerun the setup script while connected to the internet so `imageio-ffmpeg` can
install its supported binary. Avoid replacing it with an unrelated global
FFmpeg until the bundled diagnostic has been checked.

## A later shot asks for `shot_NNN.png`

For `previous_final_frame`, no per-shot storyboard image is required. Ensure the
immediately preceding normalized clip exists. For `storyboard_image`, create the
matching image under the run's `images` directory.

## Character color or face drifts

Reject the shot. Strengthen the positive immutable description, explicitly
forbid the observed drift, confirm the design keyframes match the active
profile, and regenerate from the last accepted frame. Do not hide the drift with
subtitles or cuts.

## A prop morphs during an effect

State that geometry and silhouette are locked and allow only one property to
change, such as internal brightness. If necessary, make the prop a versioned
reference asset.

## Dialogue does not fit in three seconds

Shorten the line or regenerate the delivery. A small tempo correction is
acceptable; large time stretching harms intelligibility. Verify the final mix
with speech-only transcription.

## Japanese text is garbled or invented

Do not ask the video model to draw exact text. Render reviewed text locally with
ASS/libass or another deterministic compositor.
