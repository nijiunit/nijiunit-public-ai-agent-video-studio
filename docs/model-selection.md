# Model selection

Different stages have different constraints, so one model is not assumed to be
best for every task.

| Stage | Selection priority |
|---|---|
| Story structure | instruction following, structured JSON, cost |
| Character image | exact visual constraints, editability, reference handling |
| Design motion | stable identity and visible controlled motion in three seconds |
| Story video | first-frame fidelity, motion quality, character reference support |
| TTS | pronunciation, voice consistency, completion within the shot |
| Transcription | local privacy, exact word checking |
| Subtitles/concatenation | deterministic local rendering; no generative model |

Using several models is intentional: image composition, temporal motion, speech,
and verification are different problems. A model switch must be recorded by
stage and shot in the episode's AI model usage record. Availability, price, and
input limits change; model names in `.env.example` are working examples, not a
promise that the provider will keep them available.

