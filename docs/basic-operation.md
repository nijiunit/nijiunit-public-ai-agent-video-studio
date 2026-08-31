[日本語](basic-operation.ja.md) | English

# Basic operation

Open this repository in your AI agent and choose one of two starting routes:

Your first message may be as short as "Hello" or "I want to create a video." No special command or long copied prompt is required. For a greeting alone, the agent says: "Hello. I can help you create a video with NijiUnit. First, choose how to start: use a NijiUnit tutorial or start from scratch?"

Every agent reply either continues the next safe authorized action or clearly explains why an answer is needed. It does not stop on a progress-only message such as "I checked the input" or "I will organize it." If no decision is needed, it continues working.

```text
Choose how to start: reply “Use a NijiUnit tutorial” or “Start from scratch.”
```

For a tutorial, provide one YouTube URL next. To start from scratch, describe the subject or message in one sentence.

The agent explains one operation or choice at a time. For an operation such as opening a file, it waits until that operation is finished. For an orientation or update choice, reply with the choice itself; do not add "complete." A clear natural equivalent is accepted; you do not need to reproduce the displayed example word for word.

Replies stay short and put the conclusion or current action first. When more detail is necessary, the agent uses a short numbered list and leaves optional information for a final "Additional note" section.

It is fine to leave parts unknown or undecided. The agent asks about any missing information one point at a time.

When a tutorial sample story is saved, use `input/sample_story.md` as a reference and write the desired production in ordinary prose in `input/story.md`. Name every reference image, video, or audio file and state what to use from it. You may instead describe the idea naturally and ask the agent to organize `story.md`; no Markdown syntax or long form is required. The agent safely imports an already supplied rights-cleared location, so you do not need to copy the same files again.

After you say the input is ready, the agent reads it and reports the actual story meaning, exact filenames, and role of every asset. It does not stop with only a generic acknowledgement. After rights, named characters, and the aspect ratio are ready, it asks whether to generate the paid starting images and create the Excel storyboard. On approval, it completes both without intermediate progress-only turns. Paid video generation remains blocked until you explicitly approve the workbook. An offline HTML page is available when no spreadsheet application is installed.

A new named character is reviewed one at a time from rights-cleared image or video references and fixed traits. It stays pending until you approve the character review page. Unnamed background people are not silently registered for reuse. Corrections may be written naturally in chat or entered in the yellow Excel field. The reviewed `v001` remains unchanged; the correction creates a whole `v002` run with `storyboard_v002.xlsx`. Video and audio corrections use later whole-run versions too.

If one message says, for example, "Fix S001 and then continue to video generation," the correction and continuation are treated as conditional authorization. The agent applies and verifies the correction and does not ask for the same approval again unless a new choice, cost, rights issue, or ambiguity appears.

The identity reference for a new or changed named character is the only normal image review before the workbook. Already approved characters and ordinary storyboard starting images do not add separate user checkpoints.

For an artifact review, the agent opens the containing folder and verifies the File Explorer/Finder window and exact filename itself. It then gives the exact filename and the complete review task in one concise message. For an Excel storyboard, that means open it, review every sheet, write corrections in the yellow fields and save, or report approval. It does not ask for an intermediate “Opened” reply; the next response concerns the content, correction, or approval. It never relies on “this image,” “the right image,” a process launch, or a chat attachment as proof that the intended folder is visible. Images, HTML review pages, and videos use the same verified handoff.

After approved clips are made, the finishing step handles speech, optional rights-cleared music, subtitles, final assembly, and a real nine-frame review. If the result is satisfactory, say so naturally—for example, “Looks good” or “This is finished.” The run then moves to local `history` and remains editable.

## View the finished sample

Ask “Is there a sample?” and the agent reveals the bundled 30-second MP4. The approved Excel storyboard and Japanese/English offline HTML pages are available for inspecting its construction.

```powershell
.\.venv\Scripts\python.exe run_storyboard.py show-sample --artifact video --language en
```

The sample demonstrates the finished form and workbook quality. Its characters are not silently reused in a user's production.

For a NijiUnit tutorial, the agent asks for one YouTube URL. If you do not know it, simply say so and the agent helps locate the relevant NijiUnit tutorial URL. It reads the matching official website guide directly each time and does not keep an old local tutorial cache. It can retrieve production guidance and public text, not NijiUnit's character images, source videos, or audio. When the tutorial provides a public story, the agent can save it—with your confirmation—as reference-only `input/sample_story.md`; use it to write the separate production `input/story.md` and place any named reference files beside it.

Before starting a new video production, the AI agent checks GitHub without updating:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language en
```

Only when the result is `local_behind`, the agent explains the available version, relevant changes, and local-work state before asking: "Would you like to update before starting production? Reply ‘Update’ or ‘Continue without updating.’" `local_ahead` means the local test revision is newer and is not an update offer. `diverged` requires the repository maintainer's decision. The agent reports completion only after an update succeeds. If GitHub cannot be reached, it explains that limitation and asks whether to continue with the versioned local defaults.
