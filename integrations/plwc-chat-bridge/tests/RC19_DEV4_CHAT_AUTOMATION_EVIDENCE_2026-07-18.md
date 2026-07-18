# PLwC Chat Bridge rc19.dev4 Chat Automation Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: dev3 live feedback that raw JSONL calls and JSON results still
  dominated the ChatGPT conversation and required too many manual actions
- Environment: Windows PowerShell, Chromium fixture, Node.js, Python 3.12

## rc19.dev4 Corrections

- Visible PLwC JSONL calls are replaced in the conversation by isolated PLwC
  terminal cards. The original code block is hidden, not deleted, and remains
  available through `Show JSON`.
- Marked PLwC tool results use a fenced JSON message protocol and render as one
  result card instead of raw JSON.
- Cards show tool name, PLwC icon, policy class, arguments, execution state,
  bounded result presentation and relevant actions.
- Card width reserves the open bridge panel area so the card does not render
  underneath the panel on medium desktop viewports.
- Read-only calls are automatically executed by default after the existing
  PLwC policy classification.
- Results from read-only or explicitly confirmed calls are inserted into an
  empty ChatGPT composer and submitted through the host send button.
- A non-empty composer pauses automatic result return to preserve the user's
  draft. Manual `Insert Result` remains available.
- Mutating, sandbox, reflection and unknown calls still require explicit
  confirmation. Governor `apply` remains confirmation-only.
- The Settings tab exposes separate controls for chat cards, read-only
  automatic execution and automatic result submission.
- The Bridge Primer tells ChatGPT to continue from the marked result and
  summarize it naturally instead of reproducing raw JSON.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 11 of 11 passed. |
| Extension build and tests | PASS | 31 of 31 passed, including bounded result-message parsing and automation policy regressions. |
| Python bridge contract | PASS | 6 of 6 passed. |
| Version consistency | PASS | Workspace, bridge, extension, manifest, primer and config report `0.2.0-rc19.dev4`. |

## Browser Fixture Results

The built Chromium fixture was served from IPv4 loopback and inspected at a
desktop viewport with a 260 px host chat navigation column.

| Check | Result | Observation |
| --- | --- | --- |
| Call mask | PASS | One raw `plwc_status` JSONL block produced one `PLwC CALL` card. |
| Result mask | PASS | One marked JSON result produced one `PLwC RESULT` card; exactly two total cards remained after repeated observer cycles and automatic submission. |
| Raw visibility | PASS | Both source blocks computed to `display: none`; `Show JSON` revealed and `Hide JSON` concealed the call source again. |
| Safe execution | PASS | Running the read-only fixture call reached `SUCCEEDED` and displayed `RESULT SENT`. |
| Result protocol | PASS | The composer received one `# PLwC Tool Result` message with a fenced JSON envelope and matching call ID. |
| Settings | PASS | The panel exposed all nine PLwC gateway values and three bridge-behavior checkboxes. |
| Host layout | PASS | Host navigation remained at left 0, right 260 and width 260; chat cards ended before the open bridge panel. |

## Pending Live ChatGPT Retest

The generated `extension/dist` still requires one fresh unpacked-extension
retest against the current signed-in ChatGPT DOM:

1. Reload `extension/dist` on `chrome://extensions` and reload ChatGPT.
2. Insert the newly generated rc19.dev4 Bridge Primer in a fresh conversation.
3. Request `plwc status` and confirm that one call card appears, runs, and sends
   its result without manual JSON handling.
4. Confirm that the returned user message appears as one result card and that
   ChatGPT responds with a natural-language summary.
5. Request a mutating fixture operation and confirm that it cannot run until
   the card checkbox and `Confirm & Run` action are used.
6. Confirm that the left chat menu remains reachable with the panel open and
   collapsed.
