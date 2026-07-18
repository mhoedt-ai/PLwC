# PLwC Chat Bridge rc19.dev10 Sandbox Automation And Confirmation Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: a long `plwc_sandbox_run` JSONL call appeared to be stalled while
  all existing automation settings were enabled
- Environment: Windows PowerShell, local browser fixture, Node.js and the live
  PLwC loopback bridge

## Diagnosis

The long JSON line did not block parsing or rendering. The call was classified
as `SCHEDULED` because sandbox execution deliberately remained outside the
standing write confirmation. The required checkbox and `Confirm & Run` button
were visible only after expanding the compact chat card, so the intentional
confirmation boundary looked like a stalled automation.

## rc19.dev10 Corrections

- `BridgeSettings` now has a separate, persisted `autoConfirmSandbox` option.
- The option is default-off and appears under `BRIDGE BEHAVIOR` as
  `Automatically confirm and execute PLwC sandbox operations.`
- A red warning explains that sandbox code will run without individual review
  and may execute programs or change data allowed by the local sandbox policy.
- Recognized writes and sandbox calls use separate standing confirmations.
  Unknown operations remain ineligible for automatic confirmation even when
  both settings are enabled.
- A call waiting for an individual decision uses the explicit
  `awaiting_confirmation` state and displays `! CONFIRM` in the collapsed chat
  card header.
- Enabling the appropriate standing confirmation resumes already waiting calls
  through the serialized automation queue. Disabling it during the configured
  delay returns the call to its waiting state before execution.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Full bridge workspace check | PASS | Bridge 12 of 12 and extension 45 of 45 tests passed; production builds completed. |
| Sandbox policy isolation | PASS | The sandbox setting automates only the sandbox policy; unknown operations remain manual even when both standing confirmations are enabled. |
| Desktop browser fixture | PASS | At 1280 x 720, the collapsed sandbox call displayed `! CONFIRM`, the left navigation did not overlap, and the sandbox setting was default-off with its red warning present. |
| Mobile browser fixture | PASS | At 390 x 844, the warning badge remained visible with no horizontal or card-text overflow; the panel collapsed without blocking chat. |
| Sandbox resume flow | PASS | Enabling the sandbox option resumed the waiting fixture call and the marked `plwc_sandbox_run` result was automatically submitted to the fixture composer. |
| Live loopback contract | PASS | The restarted dev10 bridge returned all eight canonical tools and `plwc_status(scope="runtime")` returned `ok=true`. |
| Live workspace root | PASS | Runtime status remained `C:\Users\USER\Claude_Arbeitsumgebung`. |

## Remaining Live Acceptance

Reload the unpacked extension from `extension/dist`, refresh ChatGPT and test a
new sandbox call in two passes: first with sandbox automation disabled to see
`! CONFIRM`, then with it enabled to verify automatic execution. The existing
write setting must not be used as evidence that sandbox automation is enabled.
