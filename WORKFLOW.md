[日本語](作業手順.md) | English

# AI video production execution contract

Updated: 2026-08-19

This repository owns basic operation, runtime code, stable defaults, safety gates, and update checks. The NijiUnit website owns the current guide for each published video. YouTube owns completed videos, activity news, and optional subscription or Hype requests. GitHub is the release and update source.

## Local operation

Read `docs/getting-started.md` for setup and `docs/basic-operation.md` for daily use. Setup validates `config/runtime-guidance/`; ordinary operation does not depend on a cached website package.

Keep a normal beginner reply to roughly two to five short sentences. Lead with the conclusion or current action. Only when more explanation is necessary, follow it with a short numbered list separated by blank lines and place optional details last under "Additional note." Omit internal work, test counts, changed-file lists, and future steps unless the current decision requires them.

Route short first messages by meaning. For a greeting alone, say: "Hello. I can help you create a video with NijiUnit. First, choose how to start: use a NijiUnit tutorial or start from scratch?" When the user already wants to create a video, do not repeat an intent question. Never require a long copied prompt or command name.

Every turn must either continue the next safe authorized action or state the concrete information, decision, authorization, correction, or approval needed from the user. A progress-only reply such as "I checked the input" is not a valid stopping point. If no question is necessary, continue. Treat an unambiguous correction plus continuation instruction as conditional authorization; verify the correction and continue without asking for the same approval again unless a new decision appears.

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

The command validates the 11-character ID, reads the matching official `/en/tutorials/{VIDEO_ID}/` page and its Markdown documents directly, and does not store a tutorial cache. If the user does not know the URL, let them say so and help locate the relevant NijiUnit tutorial URL. State that the command obtained guidance and public text only: NijiUnit's production character images, source videos, and audio are not published and must not be extracted from YouTube. When a public story is provided, ask whether to save it as reference-only `input/sample_story.md`; after the user replies “Save it,” rerun with `--write-sample-story`. Then explain that the user writes the ordinary-prose production `story.md` using the sample as reference and names every local reference file and its role. Never overwrite a different existing file. Ask one decision at a time, but group routine actions that form one review task and do not request acknowledgements merely for opening or viewing files. Do not normally re-analyze the video or read live comments. A separate analysis request requires an explanation of the API, cost/quota, public-video requirement, untrusted-input boundary, and explicit confirmation.

For the tutorial route, the user may write ordinary prose in `input/story.md` from the saved sample; for the from-scratch route or when asked, the agent may organize the user's natural-language subject into that file. Do not require Markdown syntax or a long form. If the user already supplied and authorized a local file or folder of rights-cleared reference images, videos, or audio, inventory it read-only and run `import-input`; do not ask them to copy the same files again. Record each exact filename, reference scope, fixed details, prohibited uses, source, and usage rights. For each named character, resolve the active registry or create one pending version with `register-character` and activate it only after explicit approval. When the user says input is ready, report the actual story meaning, filenames, and asset roles. Ask a concrete missing question or continue to the next decision; never stop at a generic acknowledgement. After the aspect ratio is ready, ask whether to generate the paid starting images and create the Excel storyboard, then complete both without intermediate status turns.

## Mandatory production order

1. Build and review `input/story.md`, assets, rights, and prohibited uses through the tutorial or from-scratch route.
2. Ask: "Choose the finished video's orientation. For a regular YouTube video, choose ‘Horizontal (16:9).’ For a YouTube Short, choose ‘Vertical (9:16).’ Reply ‘Horizontal’ or ‘Vertical.’" Accept an unambiguous equivalent, do not append "complete" to either choice, and pass it to `create --aspect-ratio`.
3. Generate all starting images. The agent inspects every image internally and corrects obvious identity, composition, background, continuity, text, and aspect-ratio problems. Normal production does not pause for the user's approval of one starting image.
4. Build the official Excel storyboard and Japanese/English offline HTML review pages. After input, any required new-or-changed character review, and aspect-ratio approval, the workbook is the next user-facing review.
5. Reveal the artifact and verify the exact filename. In one concise handoff,
   tell the beginner to open the workbook, review every sheet, enter corrections
   in the yellow fields and save, or report approval. Do not pause for an
   intermediate “Opened” acknowledgement.
6. Accept corrections in chat or in the yellow Excel fields. Run `apply-corrections` to create the next whole `vNNN` run, preserve the reviewed source run unchanged, place replaced images under the new run's `rejected/`, and create `storyboard_vNNN.xlsx`. Never create a new `_r002` workbook.
7. Run `approve-workbook` only after explicit user approval.
8. Generate video only after approval.
9. Build the video-review workbook from nine real frames per shot.
10. Run `finish-production` for reviewed speech, optional rights-cleared music, local sound, subtitles, the final MP4, and real nine-frame review artifacts.
11. Reveal the final artifacts. Accept a clear natural completion statement, then run `archive-production` to move the run into numbered local `history`. Keep the archived run editable.

A new or changed named character still requires its separate identity-reference approval before paid image generation. Do not add that separate checkpoint for an already approved character or an ordinary storyboard starting image. `--limit` remains available for diagnostics or recovery, not as the normal beginner review flow.

Never substitute JSON or Markdown for the Excel approval record. Never expose secrets or personal data, upload rights-unverified material, infer approval, change billing or contracts, install system software, publish, or alter repository visibility without the required explanation and confirmation. Setup, diagnosis, and explanation do not call a generation API.

Each run pins the bundled profile, aspect ratio, dimensions, studio version, and hashes. Existing runs pinned to the former website package remain readable for auditability. Work-specific people, story endings, dialogue, locations, and sound timing belong to the user's work data, not shared Python defaults.

Building the video review records a durable `awaiting_user_review` state. At a later conversation start, run `completion-status` and resume a pending final review. Explain that approval moves the production to history and that it remains revisable. Accept natural equivalents such as “Looks good,” “OK,” or “This is finished”; never require one exact sentence. A correction request is not approval.

## Whole-run versioning

The first run is `v001`. After user review, any storyboard, image, video, audio, or final correction creates the next available whole run. Keep the prior run immutable, carry unchanged approved material forward with a revision record, and preserve replaced material under the new run's `rejected/` folder. Use `apply-corrections` for storyboard changes and `revise-run --scope video|audio` for generated-media changes. Keep `storyboard_vNNN.xlsx`, `story_video_vNNN.mp4`, and `storyboard_vNNN_video.xlsx` aligned. Legacy `_r002` artifacts remain readable only. Archived runs retain their version identity and may seed a new run.

The bundled `examples/space-friends/` contains a small finished MP4, approved Excel storyboard, and Japanese/English offline HTML pages. Use `show-sample` to reveal the actual artifact when a beginner asks for a sample. The complete HOWTO production source remains in the separate movie repository.
