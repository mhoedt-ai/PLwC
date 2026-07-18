# PLwC Chat Bridge rc19.dev3 Connection And Result Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: live ChatGPT runtime-status retest after rc19.dev2
- Environment: Windows PowerShell, Chrome, Node.js, Python 3.12

## Live Findings In rc19.dev2

The browser retest confirmed that the PLwC composer icon rendered, the correct
event JSONL was detected, and `plwc_status(scope="runtime")` succeeded against
the configured workspace and active profile. It also exposed two presentation
and lifecycle defects:

1. Chrome restarted the Manifest V3 service worker after the successful call.
   The loopback listener was still alive, but the panel retained a disconnected
   transport state and the new worker no longer held the validated tool set.
2. The MCP result contained both `content[0].text` and `structuredContent`.
   Rendering the complete envelope duplicated a large runtime payload, escaped
   its JSON text, and inserted the same oversized data into the ChatGPT composer.

## rc19.dev3 Corrections

- The persistent content script checks the connection every 15 seconds.
- A restarted service worker reconnects to loopback and reloads `tools/list`
  before tool execution is unlocked again.
- An immediate tool request also reloads and validates the contract itself, so
  it does not depend on the next periodic refresh.
- Successful direct actions refresh the displayed connection status.
- MCP results prefer `structuredContent`, fall back to one parsed JSON text
  item, and retain the MCP `isError` flag separately.
- Runtime status presentation keeps the workspace, profile, policy source,
  security path, tool count, thresholds, persona-layer state, and warnings while
  omitting repeated profile inventories and the duplicate escaped text copy.
- Inserted status results use the same compact representation and a lower output
  bound.
- Non-policy MCP error results are marked failed rather than succeeded.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 11 of 11 passed. |
| Extension build and tests | PASS | 25 of 25 passed, including three MCP result normalization regressions. |
| Python bridge contract | PASS | 6 of 6 passed. |
| Version consistency | PASS | Workspace, bridge, extension, manifest, primer and config report `0.2.0-rc19.dev3`. |

## Manual Browser Retest

1. Reload `extension/dist` on `chrome://extensions` and reload ChatGPT.
2. Run `plwc_status(scope="runtime")` from a fresh JSONL call.
3. Confirm the status returns to connected automatically after an idle
   service-worker restart.
4. Confirm the panel and Insert Result action show one compact, readable result
   without escaped duplicate JSON.
