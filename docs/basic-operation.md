[日本語](basic-operation.ja.md) | English

# Basic operation

Open this repository in your AI agent and ask either:

```text
Set up this application for me.
```

```text
I want to create my own video based on this NijiUnit video.
YouTube URL: https://youtu.be/xxxxxxxxxxx
```

The agent explains one action at a time and waits for your completion reply.

For a new production, place your rights-cleared story and assets in `input/`, choose horizontal `16:9` or vertical `9:16`, review the first generated image, and then review the official Excel storyboard. Paid video generation remains blocked until you explicitly approve that workbook. An offline HTML page is available when no spreadsheet application is installed.

For a NijiUnit tutorial, the agent converts the exact YouTube ID to the matching official website guide and reads it directly each time. It does not keep using an old local tutorial cache.

Before starting a new video production, the AI agent checks GitHub without updating:

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language en
```

The agent must explain the result and obtain your confirmation before any update. If GitHub cannot be reached, it explains that limitation and asks whether to continue with the versioned local defaults.
