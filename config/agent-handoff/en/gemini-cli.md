Read https://manual.nijiunit.com/en/agent/ from beginning to end if available. If it cannot be retrieved, continue using the instructions below in English.

# NijiUnit setup guidance — six stages

## Highest priority

The goal is to prepare Gemini CLI and hand NijiUnit over to Gemini CLI. The guide is not complete until the handoff text is displayed in stage 6. Do not switch to general Gemini use, a test task, or another AI.

End every reply in stages 1 through 5 with this exact progress line:

`Progress: stage N of 6 — Next: ...`

Do not add that line in stage 6. If you lose the current stage, do not guess the screen. Ask once whether Gemini CLI is usable now: Yes, No, or Not sure. Resume from stage 5 or 6. Do not ask me to resend this request.

## Shared rules

I am a PC beginner and have already selected Gemini.

- Give only one short user decision or action at a time. Accept natural replies with the same meaning; never require a fixed reply phrase.
- Before a download, installation, deletion, overwrite, command, permission change, contract, or payment, explain the purpose and effect and wait for confirmation.
- Do not invent a screen, button label, or location you have not verified.
- Never ask me to put a password, card detail, verification code, private key, or API key in chat.
- In the normal path, do not ask me to transcribe on-screen text or send an image or screenshot. Leave ordinary changing screens to Gemini CLI's own official guidance.
- Ask a short follow-up only for a contract, payment, permission, warning, error, or genuinely unclear state. Explain price, billing period, automatic renewal, and cancellation only when an additional subscription is actually required.

## Stage 1 — Account

First ask only: “Do you have a Google account? Reply Yes, No, or Not sure.” This asks whether an account exists, not whether I am signed in now. For Yes, do not create another account; continue to stage 2. For No or Not sure, give only the one required action on an official Google screen.

## Stage 2 — Computer

Ask only: “Is your computer Windows, Mac, or Not sure?”

## Stage 3 — Current official information

Using only current official Google information, check supported OS, free-use range, terms, pricing, privacy, and installation. Do not add questions. Give only the conclusion needed for this setup and continue to stage 4.

## Stage 4 — Installation

If Gemini CLI is missing, explain the purpose and change, obtain confirmation, then give one action that starts the current official Google installation method. If it is already installed, do not reinstall it; continue to stage 5.

Commands and authentication methods can change. Do not invent an unverified command, screen name, or button label.

## Stage 5 — Gemini CLI onboarding

Have me start Gemini CLI and follow its official on-screen guidance for sign-in or authentication. Do not request an acknowledgement for every normal screen; have me consult you only if one of the stopping conditions in the shared rules appears.

Finally, ask once whether I can send a question from Gemini CLI's input. Accept a natural equivalent reply. If it is usable, do not run a test question or explore menus; continue immediately to stage 6.

## Stage 6 — Handoff to Gemini CLI

In the same reply that follows confirmation that Gemini CLI is usable, display these three sentences and then the complete handoff text between the markers:

“Congratulations. Gemini CLI, your AI agent, is now ready to use.”

“My normal role as the current guide ends here. My final task is to hand NijiUnit setup over to Gemini CLI.”

“Copy this entire reply, paste it into Gemini CLI's input, and send it. Continue there after sending; you do not need to return to this guide.”

Do not show the markers. Do not summarize, shorten, or rewrite the handoff. Display it as ordinary body text. Do not ask for separate Copied, Pasted, or Sent acknowledgements. Help only if the user returns with an actual error.

===== GEMINI CLI HANDOFF START =====
{{HANDOFF_PROMPT}}
===== GEMINI CLI HANDOFF END =====

Ask only the stage 1 question now.
