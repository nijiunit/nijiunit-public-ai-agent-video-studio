# Architecture

```text
guide-AI handoff after clone
        |
        +---- Codex ------> AGENTS.md ---+
        +---- Claude Code -> CLAUDE.md ---+--> shared language guide
        +---- Gemini CLI --> GEMINI.md ---+    agent-guide.ja.md / agent-guide.md
                                                     |
        +---- setup intent ----> Python preflight ----> setup.ps1 / setup.sh
        |                                      |
        |                                      v
        |                    bundled-default manifest/hash check
        |                                      |
        |                                      v
        |                            local doctor checks
        |                                      |
        |                                      v
        |                         guided Google API setup
        |                                      |
        |                                      v
        |                       auth + configured-model checks
        |
        +---- usage question --> docs/getting-started.md or getting-started.ja.md
        |
        +---- production ------> bundled production profile
        |                                     + local execution contract
        |                                     + work-specific input
        |
        +---- NijiUnit tutorial URL
                    ------> language-matched website guide + docs
                            fetched directly for that request
```

The three equal root entry files start after an upstream guide AI has installed
the selected agent, prepared Git, cloned the repository, and opened this folder.
They preserve the beginner-first first-message route and point to one shared
language-matched guide. The setup scripts perform idempotent local
installation. `doctor.py` verifies local dependencies, authentication, and the
configured model catalog without calling a generation API or exposing an API
key. A metadata check is not proof that paid media generation will succeed.

The repository is the production control plane. A committed manifest points to
language-matched agent guidance, a machine-readable production profile, and an
empty compatibility notice set under `config/runtime-guidance/`. `knowledge.py`
validates strict schemas, studio compatibility, and every SHA-256 before a new
run uses those defaults. Each run pins the resolved profile in
`guidance-lock.json`, so a later repository update cannot silently change a run
halfway through.

The website is the source only for published NijiUnit video lessons. Given one
YouTube URL, `website_tutorial.py` extracts its video ID, constructs the
language-matched configured URL, requires HTTPS outside loopback development,
blocks redirects and oversized responses, validates the page contract, and
downloads only same-page `docs/*.md` links. There is no daily cache and no
normal-path video or comment reanalysis. Website content is reference data,
never executable code, and cannot weaken local safety or approval gates.

```text
input story + rights-cleared references
                 |
                 v
 bundled profile + work input
                 |
                 v
          3-second storyboard
                 |
    +------------+------------+
    |                         |
    v                         v
character registry       opening image
identity + prohibitions        |
presence/action videos         |
3 timed keyframes              |
    +------------+------------+
                 v
       review/storyboard_vNNN.xlsx
       + offline ja/en HTML review
                 |
       app detection + folder reveal
       + one user action at a time
                 |
       human correction + approval
                 |
                 v
      3-second video generation
                 |
       previous final frame
                 |
                 +----> next shot
                 |
                 v
       9-frame visual review
                 |
                 v
remove provider audio -> dedicated TTS + local sound
                 |
local exact subtitles -> concatenate -> ASR + human review
```

The character-design MP4 is the authoritative review artifact. When a video
model cannot accept the opening frame and multiple motion videos reliably, the
runtime sends three timestamped frames plus the motion timing and exclusions.
`character_locks.json` records exactly which character version and motion were
selected for each shot.

`storyboard_image` starts a new visual setup. `previous_final_frame` is only for
continuing the same setup; it extracts the prior normalized clip's last frame at
the profile dimensions and uses that as the next generation's first frame.

The Excel workbook is the authoritative human-review artifact for the episode
storyboard. JSON remains the machine-readable execution format. The runtime
blocks video generation until every workbook shot has been explicitly approved
and contains no unapplied correction.

User-facing artifacts are separated from processing files. Storyboard review
workbooks and their local HTML companions live in `review/`; finished MP4s,
video-frame reviews, and model-use records live in `final/`; rejected material
lives in `rejected/`. The version unit is the complete production run. Reviewed
`v001` remains immutable; storyboard, image, video, or audio corrections create
`v002` or later, with replaced material kept under the new run's `rejected/`
folder. Names stay aligned as `storyboard_vNNN.xlsx`,
`story_video_vNNN.mp4`, and `storyboard_vNNN_video.xlsx`. Legacy `_r002`
workbooks remain readable but are not created for new productions.

The artifact handoff layer detects Excel, LibreOffice Calc, and Numbers. It
selects Excel when a spreadsheet application exists and otherwise selects the
language-matched offline HTML page. Explorer, Finder, or the Linux desktop file
manager opens the containing folder. Headless sessions return a truthful path
fallback. The application never treats a successful folder launch as user
approval.
