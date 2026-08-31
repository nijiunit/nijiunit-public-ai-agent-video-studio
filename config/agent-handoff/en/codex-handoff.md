# Handoff to Codex

This handoff asks Codex in the ChatGPT desktop app to prepare NijiUnit for a PC beginner.

I am a PC beginner. Make the public repository `https://github.com/nijiunit/nijiunit-public-ai-agent-video-studio` ready to use on this computer. Guide and explain in English.

## How to support me

Perform safe automated checks and ordinary non-destructive repository setup yourself. Do not make me run commands that you can run, and do not stop for approval after every safe command. This request authorizes obtaining the target public repository and performing ordinary non-destructive setup inside it.

Only when my judgment or action is required, briefly explain the current situation and purpose in plain language, give exactly one question or action, and wait for my reply. “One at a time” applies to my actions, not to safe work you can complete yourself.

Do not assume that a window, folder, button, or successful visual result is visible merely because a command succeeded. If you cannot inspect the screen, say so and ask only for a short state that a beginner can answer. However, when handing me off to “NijiUnit First-time Setup,” do not automate the browser or inspect its display programmatically; use the local-URL directions below.

## Project location and setup

First identify the OS and whether Git is installed using read-only checks.

On Windows, the only allowed destination is `C:\Users\[user]\Documents\Codex\NijiUnit\nijiunit-public-ai-agent-video-studio`. Replace `[user]` with the actual folder name of the signed-in Windows user. On macOS, use the signed-in user's `Documents/Codex/NijiUnit/nijiunit-public-ai-agent-video-studio` folder.

Never use a generated conversation, session, date, task, run, temporary, or `workspace` folder. Never use an attached folder, a repository opened for another task, or any copy outside the exact destination. Do not search outside the exact destination for another copy.

If the exact target does not exist, prepare it there. The public repository does not require a GitHub ID or password. If authentication is requested, do not ask me for credentials; check the source and cause.

If a folder already exists at the exact target, do not overwrite, delete, rename, or create an alternate clone. Inspect it read-only. Reuse it only if it is the correct healthy repository. Ask me only when there is a confirmed problem such as damage, a wrong source, or a conflict with my changes.

After the repository is ready, read its complete `AGENTS.md`, then all English guides, README files, setup documents, and basic-operation documents required there. Follow the checked-out repository instructions from that point onward.

Do not read any `.env` until the exact target repository has been confirmed. After confirmation, the only `.env` you may use is the one directly inside that exact repository. Never reuse or inspect an `.env` from another folder or repository.

Follow the repository scripts to prepare dependencies and diagnose the local setup. Preserve existing settings and user changes. Do not call an image, video, speech, music, or other generation API merely for setup or diagnosis.

When local preparation is complete, check whether the API key is configured without displaying it. If it is configured and I have not changed it, do not launch “NijiUnit First-time Setup,” do not ask whether to repeat setup, and continue. Launch the local masked setup page only if the key is missing, I ask to replace or redo it, or the unchanged saved setup fails a non-generation connection check. Do not launch it while another blocking state such as update `diverged` remains unresolved. When the page is needed, show the local URL printed by the launcher and tell me to copy it into the address bar of my usual browser. During this handoff, do not operate the browser, inspect the page on my behalf, or ask me to reply that it opened. Never ask me to paste an API key into chat, a terminal, a command argument, a URL, or a log; I enter it only in that local page.

## Actions that require confirmation

Explain the purpose, effect, and reversibility, and obtain my confirmation before installing system-wide software, changing permissions, deleting or overwriting files, discarding user changes, changing billing or subscriptions, making a paid generation call, changing Git remotes, pulling, merging, committing, pushing, changing visibility, or writing outside the confirmed project scope.

## When replying to me

Continue while you can act safely yourself. When I must act, report only confirmed facts, what changed, and my next single action. Only when the conditions above require the setup page, launch it, replace `<local URL>` below with the URL actually printed by the launcher, and give this guidance in one reply. Do not show this guidance for an unchanged configured key:

> “NijiUnit First-time Setup” is ready to open.
>
> Copy the following URL and paste it into the address bar of the browser you normally use:
>
> `<local URL>`
>
> Confirm that “NijiUnit First-time Setup” opens, then follow the instructions on that page to complete the Google generative AI API setup.

Do not ask me to reply that it opened; hand the normal setup flow over to the page. Only if the launcher fails, state the confirmed cause and one next action without pretending that the page opened.

Begin with read-only checks and continue as far as you safely can.
