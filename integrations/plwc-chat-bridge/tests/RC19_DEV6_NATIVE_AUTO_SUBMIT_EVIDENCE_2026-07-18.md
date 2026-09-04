# PLwC Chat Bridge rc19.dev6 Native Auto Submit Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: signed-in ChatGPT status results remained in the composer although
  automatic result submission was enabled
- Environment: Windows PowerShell, signed-in Chrome, Node.js, Chromium fixture

## Live Diagnosis

The stalled, filled ChatGPT composer was inspected without submitting its
contents. It contained one visible `#prompt-textarea` with 1,158 characters and
exactly one enabled submit control:

- `id="composer-submit-button"`
- `data-testid="send-button"`
- `aria-label="Aufforderung senden"`
- `class="composer-submit-btn composer-submit-button-color h-9 w-9"`
- owning element: ChatGPT's `form.group/composer`

This ruled out a selector or duplicate-button failure. The prior bridge called
the button's synthetic `.click()` method, but ChatGPT left the result in the
composer.

## rc19.dev6 Correction

- Auto submit now uses `form.requestSubmit(sendButton)`, preserving the real
  ChatGPT send button as the native submitter.
- Direct `.click()` remains only as a fallback for hosts without a submit form
  or for forms that reject the submitter.
- The enabled and visible button checks remain in force.
- Localized and structural selector fallbacks remain available, while `Voice`,
  `Diktat`, microphone and recording controls are rejected.
- The browser fixture now models a real submit form and prevents navigation
  while recording the submitted content.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 12 of 12 passed; the restarted loopback exposed exactly 8 canonical tools. |
| Extension typecheck | PASS | TypeScript completed without errors. |
| Extension tests | PASS | 38 of 38 passed, including native form submission and click fallback. |
| Extension production build | PASS | `extension/dist` rebuilt as `0.2.0-rc19.dev6`. |
| Browser fixture build | PASS | Fixture rebuilt with a native submit form. |
| Voice-control guard | PASS | Shared Voice and Diktat states are not treated as send controls. |

## Manual Signed-in Acceptance

Result: **PASS**, confirmed by the user in signed-in ChatGPT after loading
`0.2.0-rc19.dev6`.

- A fresh read-only status request produced a collapsed
  `PLwC-Gateway-Call` mask.
- The bridge executed `plwc_status` and submitted its result without a manual
  click.
- The submitted user message was replaced by the collapsed
  `PLwC-Gateway-Result` mask.
- ChatGPT consumed the result and returned the expected natural-language
  status summary, including the active `Sororitas` profile and 8 of 8 tools.
