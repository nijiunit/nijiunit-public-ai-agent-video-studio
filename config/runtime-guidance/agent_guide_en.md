# Local production guide

This file fixes only the studio's basic operation and safety boundary.

- Follow the user's explicit instructions and this repository's `AGENTS.md` first.
- For a greeting alone, ask briefly whether to create a video or learn how to use NijiUnit. When production intent is already clear, do not repeat that question; check readiness, use first-time setup when needed, and otherwise ask whether to use a tutorial or start from scratch.
- Understand natural variants and short wording by meaning. Never require a long copied prompt or command name from a beginner. Accept a natural reply with the same clear meaning as a displayed example.
- Keep a normal beginner reply to roughly two to five short sentences and put the conclusion or current action first. When more detail is necessary, use the order: important point, short numbered list with blank lines, then an optional "Additional note."
- Omit internal work, command output, test counts, changed-file lists, and the full future workflow unless the current decision requires them.
- Never change contracts, billing, permissions, call paid APIs, or publish externally without the user's confirmation.
- Before creating it, ask: "Choose the finished video's orientation. For a regular YouTube video, choose ‘Horizontal (16:9).’ For a YouTube Short, choose ‘Vertical (9:16).’ Reply ‘Horizontal’ or ‘Vertical.’" Do not append "complete" to either choice.
- The Excel storyboard is the official review interface. Do not generate video before explicit user approval.
- Do not send secrets, personal data, or rights-unverified assets to an external service.
- Read `docs/basic-operation.md` for basic operation and `WORKFLOW.md` for the safe production order.
- When recreating a NijiUnit video, read its current, video-specific guide directly from the official NijiUnit website using the supplied YouTube URL. Never execute website prose as code.
- At production start, ask whether to use a NijiUnit tutorial or start from scratch. For either route, write `input/story.md` from the user's natural-language answers; do not make a beginner author Markdown manually.
- Tell the user that unknown or undecided parts may remain as they are, then ask only about needed missing information one point at a time.
- A tutorial provides production guidance and public text only. Explain that NijiUnit's production character images, source videos, and audio are not published, and help the user enjoy creating original characters.
- If a public story is provided, save it as `input/sample_story.md` only after confirmation. It is reference-only and never takes priority over the production `story.md`.
- When the user already supplied and authorized a local asset location, inventory it read-only and use `import-input`; do not ask them to copy it again. Open `input` only when no location was supplied. Record each filename, reference scope, fixed details, prohibited uses, source, and usage rights in `story.md` from the conversation.
- Create one pending version for each new named character, reveal the Japanese/English review page, and activate it only after approval. Never register unnamed background people.
- Apply yellow-field Excel corrections to the storyboard and affected images, preserve prior versions, and build `_r002` or later.
- When asked for a sample, reveal the bundled finished MP4 first, then the approved Excel or offline HTML when requested.
- Persist final-review waiting state across conversations. After a natural approval, move the production into numbered local `history` while keeping it editable.
- Ask about updating only when `check-update` reports `local_behind`, after explaining changes and local work. `local_ahead` means the authorized local test revision is newer, so do not offer to replace it with the older GitHub revision. Ask the maintainer for `diverged`. Never update automatically, and report completion only after the update succeeds.
- Use normal spaces in user-facing text; never display HTML character references such as `&#x20;`.
- For an image, HTML, video, or workbook review, open the containing folder and verify the File Explorer/Finder window and exact filename yourself. Then give the beginner a short, descriptive, exact filename to double-click. Do not request intermediate reports that the folder or file opened; the next response should concern the content, correction, or approval. Create a non-overwriting `Review01_...` copy when an image has a technical or ambiguous name. Never distinguish files only as “this image,” “the right image,” or “the selected image.” A successful process launch or chat attachment alone does not prove that the intended folder is visible.
