[日本語](作業手順.md) | English

# AI video production execution contract

Updated: 2026-08-19

This repository owns basic operation, runtime code, stable defaults, safety gates, and update checks. The NijiUnit website owns the current guide for each published video. YouTube owns completed videos, activity news, and optional subscription or Hype requests. GitHub is the release and update source.

## Local operation

Read `docs/getting-started.md` for setup and `docs/basic-operation.md` for daily use. Setup validates `config/runtime-guidance/`; ordinary operation does not depend on a cached website package.

Keep a normal beginner reply to roughly two to five short sentences. Lead with the conclusion or current action. Only when more explanation is necessary, follow it with a short numbered list separated by blank lines and place optional details last under "Additional note." Omit internal work, test counts, changed-file lists, and future steps unless the current decision requires them.

Route short first messages by meaning. For a greeting alone, ask whether to create a video or learn how to use NijiUnit. When the user already wants to create a video, do not repeat that question: check readiness safely, use first-time setup when needed, and otherwise ask whether to use a tutorial or start from scratch. Never require a long copied prompt or command name.

Before every new production, check revisions without updating:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language en
```

Never update automatically. Only for `relation: local_behind`, explain the available version, relevant changes, and uncommitted local work, then ask: "Would you like to update before starting production? Reply ‘Update’ or ‘Continue without updating.’" `local_ahead` means the authorized local test revision is newer, not that an update is available; do not offer to replace it with the older GitHub revision. Stop and ask the repository maintainer for `diverged`. Do not ask for "update and complete," and report completion only after the update succeeds. If GitHub cannot be reached, explain that and ask whether to continue with the versioned local defaults.

If any shot names a character, resolve every name through the character registry before paid image or video generation. A missing registry or unresolved name is a hard stop. Review new or changed identity references before continuing, and reuse locked references and prior final frames where continuity requires them.

## NijiUnit tutorial handoff

First ask the user to choose “Use a NijiUnit tutorial” or “Start from scratch.” For the tutorial route, ask for one exact YouTube URL, then run:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://youtu.be/VIDEO_ID" --language en
```

The command validates the 11-character ID, reads the matching official `/en/tutorials/{VIDEO_ID}/` page and its Markdown documents directly, and does not store a tutorial cache. State that it obtained guidance and public text only: NijiUnit's production character images, source videos, and audio are not published and must not be extracted from YouTube. When a public story is provided, ask whether to save it as reference-only `input/sample_story.md`; after the user replies “Save it,” rerun with `--write-sample-story`. Never overwrite a different existing file. Explain one action at a time. Do not normally re-analyze the video or read live comments. A separate analysis request requires an explanation of the API, cost/quota, public-video requirement, untrusted-input boundary, and explicit confirmation.

For both routes, ask for the subject in natural language and write `input/story.md` for the user. If the user has rights-cleared reference images, videos, or audio, open the actual `input` folder, have them place the files there, and record each filename, reference scope, fixed details, prohibited uses, source, and usage rights. Use `templates/story-input.md` as internal structure; do not make the beginner fill in Markdown. For each named character, resolve the active registry or create one pending version with `register-character`, reveal its review page, and activate it with `approve-character` only after explicit approval. A changed design becomes `v002` or later, while unnamed background people are not registered. Show the complete input summary for correction or approval before `create`.

## Mandatory production order

1. Build and review `input/story.md`, assets, rights, and prohibited uses through the tutorial or from-scratch route.
2. Ask: "Choose the finished video's orientation. For a regular YouTube video, choose ‘Horizontal (16:9).’ For a YouTube Short, choose ‘Vertical (9:16).’ Reply ‘Horizontal’ or ‘Vertical.’" Accept an unambiguous equivalent, do not append "complete" to either choice, and pass it to `create --aspect-ratio`.
3. Generate and review only the first starting image.
4. After agreement, generate the remaining starting images.
5. Build the official Excel storyboard and Japanese/English offline HTML review pages.
6. Reveal the artifact and give the beginner one action, then wait.
7. Run `apply-corrections`, preserve replaced images under `rejected/`, and create a new `_r002`, `_r003`, or later workbook; never overwrite.
8. Run `approve-workbook` only after explicit user approval.
9. Generate video only after approval.
10. Build the video-review workbook from nine real frames per shot.
11. Run `finish-production` for reviewed speech, optional rights-cleared music, local sound, subtitles, the final MP4, and real nine-frame review artifacts.
12. Reveal the final artifacts. Accept a clear natural completion statement, then run `archive-production` to move the run into numbered local `history`. Keep the archived run editable.

Never substitute JSON or Markdown for the Excel approval record. Never expose secrets or personal data, upload rights-unverified material, infer approval, change billing or contracts, install system software, publish, or alter repository visibility without the required explanation and confirmation. Setup, diagnosis, and explanation do not call a generation API.

Each run pins the bundled profile, aspect ratio, dimensions, studio version, and hashes. Existing runs pinned to the former website package remain readable for auditability. Work-specific people, story endings, dialogue, locations, and sound timing belong to the user's work data, not shared Python defaults.

Building the video review records a durable `awaiting_user_review` state. At a later conversation start, run `completion-status` and resume a pending final review. Explain that approval moves the production to history and that it remains revisable. Accept natural equivalents such as “Looks good,” “OK,” or “This is finished”; never require one exact sentence. A correction request is not approval.

The bundled `examples/space-friends/` contains a small finished MP4, approved Excel storyboard, and Japanese/English offline HTML pages. Use `show-sample` to reveal the actual artifact when a beginner asks for a sample. The complete HOWTO production source remains in the separate movie repository.
