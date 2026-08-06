# Architecture

```text
guide-AI handoff after clone
        |
        v
     AGENTS.md
        |
        +---- setup intent ----> Python preflight ----> setup.ps1 / setup.sh
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
        +---- production ------> input + WORKFLOW.md or 作業手順.md
```

`AGENTS.md` starts after an upstream guide AI has installed the agent, prepared
Git, cloned the repository, and opened this folder. It routes user intent and
requires one user action at a time. The setup scripts perform idempotent local
installation. `doctor.py` verifies local dependencies, authentication, and the
configured model catalog without calling a generation API or exposing an API
key. A metadata check is not proof that paid media generation will succeed.

```text
input story + rights-cleared references
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
1280×720 and uses that as the next generation's first frame.
