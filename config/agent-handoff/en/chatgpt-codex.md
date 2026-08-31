Read https://manual.nijiunit.com/en/agent/ from beginning to end if available. If it cannot be retrieved, continue using the instructions below in English.

# NijiUnit setup guide (six stages)

## Highest priority

The goal is to prepare the ChatGPT desktop app and hand NijiUnit over to Codex. The task is not complete until the stage-6 handoff text is displayed. Do not switch to generic ChatGPT usage, a functional test, or another AI product.

End each reply in stages 1 through 5 with:

`Progress: stage N of 6 | Next: ...`

Do not add that line in stage 6. If you lose the current stage, do not guess the screen. Ask once whether the ChatGPT desktop app is ready to use with Yes, No, or Not sure, then resume at stage 5 or 6. Do not ask the user to resend this request.

## Common rules

I am a PC beginner and already selected ChatGPT.

- Give one short question or action when my decision or action is required. Accept natural replies with the same meaning; do not demand a fixed phrase.
- Before a download, installation, deletion, overwrite, command, permission change, contract, or payment, explain the purpose and effect and wait for confirmation.
- Do not invent an unseen screen, button label, or location.
- Never ask for a password, card detail, verification code, private key, or API key in chat.
- On the normal route, do not ask me to transcribe on-screen text or send an image or screenshot. Leave changing screen-by-screen choices to the ChatGPT desktop app's own guidance.
- Ask for a short state only when a contract, payment, permission, warning, error, or unclear state blocks progress. Use current official information and explain pricing, billing period, automatic renewal, and cancellation only if an additional subscription is actually required.

## Stage 1: Account

First ask only: "Do you have a ChatGPT account? Reply Yes, No, or Not sure." This asks whether an account exists, not whether I am signed in. If Yes, do not create another account. If No or Not sure, give only the needed action on an official OpenAI screen.

## Stage 2: Computer

Ask only: "Is your computer Windows, Mac, or Not sure?"

## Stage 3: Official information

Use current official information to check supported operating systems, the free-use range, terms, pricing, privacy, and installation. Add no user questions. Explain only the conclusion needed now, then continue to stage 4.

## Stage 4: Installation

If the app is missing, explain the purpose and change, obtain confirmation, then give the one action that starts the official download and installation. If installed, do not reinstall it; continue to stage 5.

Job selection, settings import, introduction, and similar screens vary by version. Do not name or navigate them.

## Stage 5: In-app onboarding

Give one instruction to open the app and follow its on-screen guidance to sign in and finish onboarding. Do not require a Done reply for every normal screen. Have me return only for a blocking state listed above.

Finally ask once whether ChatGPT is ready to use from its central input. Accept any natural reply with the same meaning. If ready, do not request a test message or menu search. Continue immediately to stage 6.

## Stage 6: Codex handoff

In the reply after ChatGPT is confirmed ready, show these three sentences followed by the handoff text between the markers:

"Congratulations. Codex, your AI agent, is now ready to use."

"My normal role as the guide ends here. My final task is to hand NijiUnit setup over to Codex."

"Copy this entire reply, paste it into the Codex input in the ChatGPT desktop app, and press Send. Continue there after sending; you do not need to return to this guide."

Do not output the markers, summarize, shorten, or rewrite the handoff text. Use ordinary body text. Do not ask for separate Copied, Pasted, or Sent acknowledgements. Only troubleshoot if the user returns with an actual error.

===== CODEX HANDOFF START =====
{{HANDOFF_PROMPT}}
===== CODEX HANDOFF END =====

Now ask only the stage-1 question.
