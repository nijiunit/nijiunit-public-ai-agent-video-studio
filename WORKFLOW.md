[日本語](作業手順.md) | English

# AI video production execution contract

Updated: 2026-08-19

This repository owns basic operation, runtime code, stable defaults, safety gates, and update checks. The NijiUnit website owns the current guide for each published video. YouTube owns completed videos, activity news, and optional subscription or Hype requests. GitHub is the release and update source.

## Local operation

Read `docs/getting-started.md` for setup and `docs/basic-operation.md` for daily use. Setup validates `config/runtime-guidance/`; ordinary operation does not depend on a cached website package.

Before every new production, check revisions without updating:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language en
```

Never update automatically. Explain the difference and uncommitted local work, then ask the user before any pull, merge, or installation. If GitHub cannot be reached, explain that and ask whether to continue with the versioned local defaults.

If any shot names a character, resolve every name through the character registry before paid image or video generation. A missing registry or unresolved name is a hard stop. Review new or changed identity references before continuing, and reuse locked references and prior final frames where continuity requires them.

## NijiUnit tutorial handoff

Ask for one exact YouTube URL, then run:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://youtu.be/VIDEO_ID" --language en
```

The command validates the 11-character ID, reads the matching official `/en/tutorials/{VIDEO_ID}/` page and its Markdown documents directly, and does not store a tutorial cache. Explain one action at a time. Do not normally re-analyze the video or read live comments. A separate analysis request requires an explanation of the API, cost/quota, public-video requirement, untrusted-input boundary, and explicit confirmation.

## Mandatory production order

1. Review the story, assets, and rights in `input/`.
2. Ask for horizontal `16:9` or vertical `9:16`; pass it to `create --aspect-ratio`.
3. Generate and review only the first starting image.
4. After agreement, generate the remaining starting images.
5. Build the official Excel storyboard and Japanese/English offline HTML review pages.
6. Reveal the artifact and give the beginner one action, then wait.
7. Apply corrections and create a new `_r002`, `_r003`, or later workbook; never overwrite.
8. Run `approve-workbook` only after explicit user approval.
9. Generate video only after approval.
10. Build the video-review workbook from nine real frames per shot.
11. Finish the MP4, model-use record, and pre-publication checks.

Never substitute JSON or Markdown for the Excel approval record. Never expose secrets or personal data, upload rights-unverified material, infer approval, change billing or contracts, install system software, publish, or alter repository visibility without the required explanation and confirmation. Setup, diagnosis, and explanation do not call a generation API.

Each run pins the bundled profile, aspect ratio, dimensions, studio version, and hashes. Existing runs pinned to the former website package remain readable for auditability. Work-specific people, story endings, dialogue, locations, and sound timing belong to the user's work data, not shared Python defaults.
