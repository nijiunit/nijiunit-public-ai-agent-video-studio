[日本語](basic-operation.ja.md) | English

# Basic operation

Open this repository in your AI agent and choose one of two starting routes:

Your first message may be as short as "Hello" or "I want to create a video." No special command or long copied prompt is required. For a greeting alone, the agent says: "Hello. I can help you create a video with NijiUnit. Reply ‘Create a video’ or ‘Learn how to use it.’" When production intent is already clear, it does not ask that question again; it checks readiness and proceeds to the tutorial-or-from-scratch choice.

```text
Choose how to start: reply “Use a NijiUnit tutorial” or “Start from scratch.”
```

For a tutorial, provide one YouTube URL next. To start from scratch, describe the subject or message in one sentence.

The agent explains one operation or choice at a time. For an operation such as opening a file, it waits until that operation is finished. For an orientation or update choice, reply with the choice itself; do not add "complete." A clear natural equivalent is accepted; you do not need to reproduce the displayed example word for word.

Replies stay short and put the conclusion or current action first. When more detail is necessary, the agent uses a short numbered list and leaves optional information for a final "Additional note" section.

It is fine to leave parts unknown or undecided. The agent asks about any missing information one point at a time.

For either route, describe the subject naturally and let the agent write `input/story.md`. If you have rights-cleared reference images, videos, or audio, the agent opens the actual `input` folder and records what each file should and should not be used for. You do not need to author Markdown manually. The agent then asks: "Choose the finished video's orientation. For a regular YouTube video, choose ‘Horizontal (16:9).’ For a YouTube Short, choose ‘Vertical (9:16).’ Reply ‘Horizontal’ or ‘Vertical.’" Review the first generated image and then the official Excel storyboard. Paid video generation remains blocked until you explicitly approve that workbook. An offline HTML page is available when no spreadsheet application is installed.

A new named character is reviewed one at a time from rights-cleared image or video references and fixed traits. It stays pending until you approve the character review page. Unnamed background people are not silently registered for reuse. Corrections entered in the yellow Excel field are applied to the storyboard and affected images, then a new `_r002` or later workbook is built without overwriting the earlier review.

After approved clips are made, the finishing step handles speech, optional rights-cleared music, subtitles, final assembly, and a real nine-frame review. If the result is satisfactory, say so naturally—for example, “Looks good” or “This is finished.” The run then moves to local `history` and remains editable.

## View the finished sample

Ask “Is there a sample?” and the agent reveals the bundled 30-second MP4. The approved Excel storyboard and Japanese/English offline HTML pages are available for inspecting its construction.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py show-sample --artifact video --language en
```

The sample demonstrates the finished form and workbook quality. Its characters are not silently reused in a user's production.

For a NijiUnit tutorial, the agent converts the exact YouTube ID to the matching official website guide and reads it directly each time. It does not keep using an old local tutorial cache. It can retrieve production guidance and public text, not NijiUnit's character images, source videos, or audio. Enjoy creating your own characters instead of copying unpublished NijiUnit assets. When the tutorial provides a public story, the agent can save it—with your confirmation—as reference-only `input/sample_story.md`; the production always uses a separate `input/story.md`.

Before starting a new video production, the AI agent checks GitHub without updating:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language en
```

The agent must explain the available version, relevant changes, and local-work state before asking: "Would you like to update before starting production? Reply ‘Update’ or ‘Continue without updating.’" It reports completion only after the update succeeds. If GitHub cannot be reached, it explains that limitation and asks whether to continue with the versioned local defaults.
