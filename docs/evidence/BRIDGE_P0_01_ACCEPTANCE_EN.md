# Chat Bridge P0-01 Acceptance Evidence

Date: 2026-07-30

Scope: BRIDGE-P0-01 only. Chunked result transfer (BRIDGE-P0-02), Primer work,
Windows Setup, and the final release test remain outside this acceptance pass.

## Outcome

BRIDGE-P0-01 implementation acceptance passes for the extension and loopback
workspace.

Chat tool-call identity is now exactly `(conversation_id, call_id)`. Tool name
and arguments form a separate payload signature. An exact duplicate is ignored
by observation and rejected by the authoritative background claim registry
before it can reach the loopback Bridge. Reusing an identity with a changed tool
name or changed arguments is reported as a visible conflict and is never
forwarded.

Claims are serialized in the extension background and persisted in
`chrome.storage.local` before the WebSocket request begins. This prevents a
second execution across tabs, extension/background reconnects, and browser
restarts. Corrupt or over-capacity registry data locks execution instead of
silently reopening old identities.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Identity is `(conversation_id, call_id)` | PASS | `tool-call-parser.ts` exposes one stable identity key and a separate payload signature. Parser tests verify the same call ID is independent across conversations. |
| Exact duplicate executes at most once | PASS | `tool-call-observer.ts` ignores an already registered identity. `tool-call-execution-registry.ts` persists a claim before forwarding and rejects a restored duplicate after JSON/storage round-trip. |
| Changed name or arguments are a conflict | PASS | Observer and registry tests cover changed arguments and changed tool name. `PlwcPanel.offerToolCallConflict` moves the run to a visible `CONFLICT` state and execution guards admit only scheduled or confirmation-waiting calls. |
| Processed calls remain done after reconnect/restart | PASS | The background registry is stored in `chrome.storage.local`, claims are serialized, and malformed/full registry state fails closed. Existing result messages also restore terminal run state in chat cards. |
| Old chat calls are not reclassified as new | PASS | The startup baseline records existing calls without offering them. Returning to a previous conversation preserves the per-conversation registry. |
| Late history hydration remains silent | PASS | The timed baseline tests cover delayed old calls and admit only a call that appears after the baseline closes. |
| Conversation switch isolates equal call IDs | PASS | Conversation-aware parser, observer, and registry tests verify that the same `call_id` in a different conversation is a distinct identity. |
| Browser lifecycle fixture covers required scenarios | PASS | `tests/browser/p0-01-browser-acceptance.ts` covers browser registry restoration, old chat, chat switch/return, delayed hydration, and payload conflict. The harness runs in the automated extension suite and is bundled into the browser fixture, which exposes `data-plwc-p0-01-acceptance="pass"` on success. |
| Legacy JSONL browser fixture removed | PASS | `tests/browser/fixture.html` now uses the canonical `plwc_tool_call` wrapper for status and sandbox calls. |

## Verification Commands

Executed in
`<REPOSITORY_ROOT>\integrations\plwc-chat-bridge\extension`:

```powershell
npm run typecheck
```

Result: passed.

```powershell
npm test
```

Result: 101 passed.

```powershell
npm run build:fixture
```

Result: passed; the fixture was built at
`extension\.browser-fixture`.

Executed in `<REPOSITORY_ROOT>\integrations\plwc-chat-bridge`:

```powershell
npm run check
```

Result: loopback Bridge build and 20 tests passed; extension production build
and the full extension test suite passed.

```powershell
git diff --check -- <BRIDGE-P0-01 files>
```

Result: passed with Git LF/CRLF conversion warnings only.

## Browser Smoke Note

The built fixture could not be opened through the in-app browser because that
browser rejects local `file:` URLs by policy. No bypass was attempted. The
browser lifecycle harness is nevertheless compiled into the fixture and runs
in the automated test suite; a manual visual smoke run remains a release-level
check on a browser surface that permits the local fixture.

## Non-P0-01 Items

- No version bump to 1.0.0 was performed.
- No Windows Setup changes were made.
- BRIDGE-P0-02 chunk transport was not modified by this pass.
- Primer and build-identity work remain separate follow-up items.
