# PLwC Chat Bridge rc19.dev7 Automation Timing And Retry Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: an automatically confirmed `plwc_workspace_operation` succeeded,
  but ChatGPT rejected the first automatic result submission
- Environment: Windows PowerShell, signed-in Chrome, Node.js, Chromium fixture

## Live Diagnosis

The failed write round trip created `Wandorra\Fahrzeugkampf` successfully and
inserted an 872-character PLwC result into the ChatGPT composer. The panel
reported `Result inserted, but ChatGPT did not accept the automatic
submission.` Live inspection then found one visible, enabled submit button and
no active assistant stream. This proved that the one-shot native submit had
run too early and never retried after ChatGPT became ready.

## rc19.dev7 Corrections

- The three upstream MCP SuperAssistant timing controls are available under
  `Bridge Behavior`: `Auto-execute delay`, `Auto-insert delay` and
  `Auto-submit delay`.
- Values are persisted immediately in seconds, accept tenths from 0 through
  60 and default to 2 seconds.
- Existing behavior settings, including automatic write confirmation, survive
  the settings-revision migration.
- Automatic execution waits before running a detected call, result insertion
  waits after the tool completes, and the first submit waits after insertion.
- A rejected submit is retried up to six times, alternating native
  `form.requestSubmit(sendButton)` and direct button activation.
- Submission is successful only after the composer is actually empty. A merely
  disabled button is no longer treated as success.
- Stop, cancel and generation controls are excluded alongside Voice and Diktat
  controls.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 12 of 12 passed. |
| Extension typecheck | PASS | TypeScript completed without errors. |
| Extension tests | PASS | 41 of 41 passed, including rejected-submit retry and timing bounds. |
| Extension production build | PASS | `extension/dist` rebuilt as `0.2.0-rc19.dev7`. |
| Browser fixture build | PASS | Fixture rebuilt with the three timing controls. |
| Version consistency | PASS | Bridge, extension, manifest, shared contract and package metadata report `0.2.0-rc19.dev7`. |
| Restarted loopback runtime | PASS | `ws://127.0.0.1:3007/message` returned the canonical 8 of 8 public PLwC tools. |

## Manual Signed-in Acceptance

Pending after loading `0.2.0-rc19.dev7`. Use a fresh governed write operation
in a disposable path and verify that its result leaves the composer without a
manual click, including when the first submission is transiently rejected.
