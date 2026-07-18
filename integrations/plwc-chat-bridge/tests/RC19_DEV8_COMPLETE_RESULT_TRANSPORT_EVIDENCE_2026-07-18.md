# PLwC Chat Bridge rc19.dev8 Complete Result Transport Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: a successful full profile compile reached ChatGPT only as a
  bridge-generated 4,000-character preview
- Environment: Windows PowerShell, Node.js, PLwC loopback bridge

## Defect

`formatPlwcToolResultMessage()` replaced every result message over 12,000
characters with a preview carrying `"truncated_by": "PLwC Chat Bridge"`.
This did not alter the profile stored by PLwC, but it did remove the remainder
of `compiled_layer` from the result supplied to ChatGPT. ChatGPT therefore did
not receive the complete tool output.

## rc19.dev8 Correction

- The marked `# PLwC Tool Result` transport serializes the complete normalized
  result without bridge-side character truncation.
- Compact terminal cards remain display-bounded. Their visual limit does not
  mutate the hidden source message or the result sent to ChatGPT.
- A regression test sends a full compile envelope larger than 12,000
  characters and verifies exact parse round-trip equality.
- The synthetic result must not contain a `truncated_by` marker.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | Build completed and 12 of 12 tests passed. |
| Extension tests | PASS | 41 of 41 passed, including exact oversized compiled-layer round trip. |
| Extension production build | PASS | `extension/dist` rebuilt as `0.2.0-rc19.dev8`. |
| Loopback runtime | PASS | Restarted dev8 runtime returned the canonical 8 of 8 public tools. |

## Manual Signed-in Acceptance

Pending after loading `0.2.0-rc19.dev8`. Run `plwc_profile` with a full compile
and verify that the submitted result has no bridge truncation marker and that
ChatGPT can inspect content beyond the former 4,000-character preview boundary.
