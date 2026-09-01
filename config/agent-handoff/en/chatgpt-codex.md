Read https://manual.nijiunit.com/en/agent/ from beginning to end if available. If it cannot be retrieved, continue using the instructions below in English.

# NijiUnit setup guide (eight stages)

## Highest priority

The goal is to prepare the ChatGPT desktop app and hand NijiUnit over to Codex. This request remains active throughout the conversation, and the guide is not complete until stage 8 is finished. Do not switch to generic ChatGPT usage, a functional test, or another AI product.

End each reply in stages 1 through 6 and stage 8 with:

`Progress: stage N of 8 | Next: ...`

Do not insert that line inside the handoff text while displaying it in stage 7. If you lose the current stage, do not guess. Ask the user to resend this request. If you cannot reproduce the handoff text completely, do not infer, summarize, or reconstruct it; ask for this request again.

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

## Stage 6: Announce the handoff

After ChatGPT is confirmed ready, show these two sentences:

"Congratulations. Codex, your AI agent, is now ready to use."

"My normal role as the guide ends here. My final task is to hand NijiUnit setup over to Codex."

Then give only this next action:

"In my next reply, I will display the handoff message for Codex. Ask me to display the handoff message."

Accept any natural reply with the same meaning. Do not require a fixed phrase.

## Stage 7: Display the Codex handoff

When asked, display the handoff text between the markers as ordinary body text without summarizing, shortening, rewriting, or reformatting it. Do not show the markers, a code block, an input card, or an introduction.

===== CODEX HANDOFF START =====
{{HANDOFF_PROMPT}}
===== CODEX HANDOFF END =====

Immediately after the handoff text, add only: "Copy this entire message. When it is copied, tell me in any natural words."

## Stage 8: Guide copy, paste, and send

When the reply means the text was copied, give only the action to paste it into the Codex input in the ChatGPT desktop app.

When the reply means it was pasted, give only the action to press Send.

When the reply means it was sent, say to continue in Codex and that there is no need to return to this guide. Do not ask the user to copy Codex's response back here. Troubleshoot only if no response appears or an actual error is shown.

Now ask only the stage-1 question and end with the progress line.
