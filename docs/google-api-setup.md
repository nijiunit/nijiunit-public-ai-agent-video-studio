English | [日本語](google-api-setup.ja.md)

# First-time Google Generative AI API setup

Last reviewed: 2026-08-06

This internal guide begins after the repository has been cloned. It tells an AI agent how to assist a beginner. Google screens and prices can change; the live screen and current official documentation are authoritative.

## What this application needs

The application uses different Gemini API models for story planning, images, video, and speech. Default model identifiers are bundled in the SHA-256-verified `config/runtime-guidance/production_profile.json`. Video generation may require paid access, so creating an API key alone is insufficient; the current price and billing state of the selected Google Cloud project must also be reviewed.

Official references:

- [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing)
- [Current Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Google AI Studio API Keys](https://aistudio.google.com/app/apikey)
- [Troubleshooting Google AI Studio](https://ai.google.dev/gemini-api/docs/troubleshoot-ai-studio)

## Conversation rules for the AI agent

- Do not present the entire procedure at once.
- When the user must operate a screen, explain one action per response and wait for completion.
- If the screen differs from the guide, ask for the visible heading or button label before continuing.
- Never ask the user to enter a Google password, verification code, card details, or API key into chat.
- Do not choose a contract, country, payment method, Prepay/Postpay option, deposit, or automatic top-up on the user's behalf.
- When discussing prices, state the review date and link to the official pricing page. The live Google screen is the final authority.
- If the user declines billing, stop and report: "The public demo and local tools are available; the video-generation API is not configured."

## G1: Open NijiUnit First-time Setup

As soon as the local environment reaches `LOCAL READY`, the AI agent does not first ask about a Google account or pricing in chat. It runs the command for the user's platform and opens the illustrated local setup page. A beginner does not operate a terminal.

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\open_setup.py --language en
```

macOS or Linux:

```bash
./.venv/bin/python scripts/open_setup.py --language en
```

After confirming that the page is visible, let the user follow its on-screen guidance. Do not operate Google AI Studio on the user's behalf or replace the page flow with a chat-only walkthrough.

## G2: Confirm a Google account on the page

Ask only whether the user can access Google AI Studio with an account they personally control over time. Explain that managed work or school accounts may be restricted by an administrator.

If the user has no account, direct them to Google's official account-creation flow. The user performs account creation, identity verification, and password entry personally.

## G3: Open Google AI Studio from the setup page

The user opens [Google AI Studio API Keys](https://aistudio.google.com/app/apikey) from the local setup page. If a sign-in or terms screen appears, handle that screen before proceeding.

For a new user, accepting the terms may create a default Google Cloud project and API key. Existing Google Cloud users may need to import or select the intended project.

## G4: Review pricing and paid use

Before beginning billing setup, explain these points one at a time:

- Gemini API has free and paid tiers.
- Verify the paid-access requirement and current pricing of the video model configured in the bundled profile against Google's official information.
- Text, image, video, and audio use different pricing units.
- Prepay purchases balance in advance; Postpay bills after usage.
- Automatic top-up can create continuing charges.
- Current prices, minimum deposits, taxes, and limits must be confirmed on the live Google screen.

Prices change, so this repository does not treat a recorded price as authoritative. Check the model ID in the bundled profile, then verify its current unit price and billing unit on Google's official pricing page and the live Google screen before agreeing.

After the explanation, ask the user to choose either "continue with paid setup" or "stop here."

## G5: Configure project billing

Only if the user chooses paid setup, guide them to `Set up billing` for the intended project.

Review country, terms, contact information, payment method, Prepay/Postpay, and deposit one screen at a time. The user enters card information and completes identity verification directly on Google's screen. It must never be entered into the AI-agent conversation.

Afterward, confirm with the user that the intended project shows the appropriate paid plan or billing tier in the API Keys or Projects screen. For Prepay, also confirm that usable balance is present. If billing activation is delayed, wait and recheck rather than repeatedly changing settings.

## G6: Prepare and store an API key safely

If a suitable key already exists for the selected project, do not create a duplicate. Use `Create API key` only when required.

Current newly created Google AI Studio keys are authentication keys. The user copies the key, returns to the still-open NijiUnit page, and pastes it into the masked local field. Never ask for the key itself or have it pasted into chat.

The page binds only to `127.0.0.1`. It does not put the key in a URL, log, or browser storage and stores it only in the Git-ignored `.env`. It requires explicit confirmation before replacing an existing key. Use `configure_api_key.py` only as a recovery path when the browser page cannot run.

## G7: Verify authentication and model configuration

For a new key, the user presses **Save on this PC and check connection** on the same page. For an existing key, the user presses **Check the saved connection**. This check generates no media. It authenticates the key and verifies that the configured story, image, video, TTS, and speech-review model identifiers appear in the model catalog. It does not perform paid generation. Use `doctor.py --require-api-key --verify-api-key-online` only as a recovery path if the page cannot run.

A model-catalog check cannot guarantee sufficient balance, regional support, quota, preview eligibility, or successful generation. Report the result as "paid generation not tested." Before the first image or video request, tell the user that charges may apply and confirm the generation request.

## Completion states

- `LOCAL READY (Google API setup required)`: the local runtime and bundled defaults are ready; Google API is not configured
- `LOCAL READY (online verification required)`: key stored, Google connection not verified
- `READY FOR GENERATION (paid generation not tested)`: authentication and configured model identifiers verified; paid generation not run
- `NOT READY`: at least one issue remains

Even the third state must not be described as a successful paid generation. Actual generation is verified only after the first user-approved generation succeeds.
