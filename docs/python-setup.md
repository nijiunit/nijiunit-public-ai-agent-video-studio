English | [日本語](python-setup.ja.md)

# First-time Python setup

Last reviewed: 2026-08-06

This is an internal guide for an AI agent assisting a beginner whose computer does not yet have a compatible Python installation. Do not show every step at once. Give the user one action, wait for completion, and then continue.

## Shared rules

- Python 3.11 or later is required.
- If a compatible version already exists, do not install another Python.
- Explain the change and obtain the user's confirmation before installing system software.
- Use an official distribution source or the operating system's standard package-management channel.
- Never ask the user to enter an administrator password, Apple ID, or Microsoft account credential into chat.
- On a managed work or school computer, stop and ask the user to consult the administrator if software installation is restricted.

## Windows

Official reference: [Using Python on Windows](https://docs.python.org/3/using/windows.html)

### What the AI agent runs first

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Only if it reports `[ACTION_REQUIRED] Python 3.11 or later is not installed.`, ask the user one question:

> This computer does not yet have the Python version required by this tool. May I install Python 3.13 through Python's official Install Manager or the official Windows Package Manager channel?

Only after the user agrees, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallPython
```

If `ACTION_REQUIRED` asks for a terminal restart, explain only how to close and reopen the AI agent or terminal. Then run the ordinary `setup.ps1` again.

If Windows Package Manager is unavailable, use the [official Python downloads for Windows](https://www.python.org/downloads/windows/) and the Python Install Manager. Ask the user to open the page, confirm what is visible, and guide download, installation, and terminal restart one action at a time.

## macOS

Official reference: [Using Python on macOS](https://docs.python.org/3/using/mac.html)

If `bash scripts/setup.sh` reports that Python is missing, guide these actions one at a time:

1. Ask the user to open the official macOS Python guide and wait.
2. Ask the user to choose the signed macOS installer distributed by `python.org`.
3. Wait for the download to finish.
4. Ask the user to open the `.pkg` and verify the displayed publisher and destination.
5. Let the user perform macOS authorization. Never request the password in chat.
6. After installation, follow the official guide to run `Install Certificates.command`.
7. Reopen the AI agent or terminal and run `bash scripts/setup.sh` again.

## Completion condition

Python preparation is complete when setup step `[1/6]` displays Python 3.11 or later and proceeds to create `.venv`. Do not report that the entire application is ready merely because Python has been installed.
