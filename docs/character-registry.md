# Character registry

Each active character points to an immutable versioned profile.

```text
characters/
  registry.json
  registry.lock.json
  character_id/
    v001/
      profile.json
      references/identity.png
      design_videos/v001/
        start_frame.png
        design_presence.mp4
        design_presence_keyframes/{start,mid,end}.jpg
        action_name.mp4
        action_name_keyframes/{start,mid,end}.jpg
```

`design_presence` is always selected to stabilize resting posture, material
response, blink/breathing scale, and movement weight. It must not force the
exact idle gesture into every story shot. An action motion is added only when a
trigger matches the shot text.

Anti-examples document known mistakes but are never generation inputs. Describe
the correction in `forbidden_traits` and provide the positive authoritative
reference instead.

Run `validate-characters` after every profile or asset change. The lock file
stores active versions and SHA-256 hashes so a production record can identify
the exact visual inputs.

