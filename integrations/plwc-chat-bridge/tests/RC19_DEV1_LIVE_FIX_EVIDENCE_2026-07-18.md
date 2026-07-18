# PLwC Chat Bridge rc19.dev1 Live Fix Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Base commit: `818a724`
- Trigger: live unpacked-extension test on the ChatGPT web UI
- Environment: Windows PowerShell, Node.js `v24.15.0`, Python `3.12.10`

## Live Findings In rc19.dev0

The live ChatGPT test confirmed that the panel mounted, the primer was inserted,
the live schema hash was generated, and the eight-tool contract was loaded. It
also exposed four integration defects:

1. ChatGPT followed the primer and emitted a direct `name`/`arguments` object,
   while the fail-closed parser accepted only event-based JSONL. The requested
   status call was therefore not queued.
2. The panel icon was unavailable inside the host page because the extension
   resource was not declared as web-accessible for the ChatGPT hosts.
3. The MV3 WebSocket became disconnected while the local listener remained
   alive on `127.0.0.1:3007`.
4. Event-based calls already present in the open conversation were offered as
   scheduled calls after the extension loaded. They still required explicit
   confirmation and were not executed, but they cluttered the current session.

## rc19.dev1 Corrections

- The primer now requires one fenced `jsonl` block per call, using
  `function_call_start`, one `parameter` event per argument, and
  `function_call_end` with one shared unique call ID.
- The generated `plwc_status` mask uses `scope="runtime"` instead of an empty
  status scope.
- Direct `name`/`arguments` objects remain rejected by the parser.
- The canonical PLwC icon is web-accessible only on `chatgpt.com` and
  `chat.openai.com`.
- Calls present when the observer starts are recorded as the session baseline
  and are not offered for execution. Only calls appearing afterward enter the
  queue.
- An active connection sends a JSON-RPC `ping` every 20 seconds to keep the MV3
  WebSocket session alive.
- The integration version was advanced consistently to `0.2.0-rc19.dev1`.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge tests | PASS | 10 of 10 passed. |
| Extension tests | PASS | 18 of 18 passed, including two new observer-baseline regressions. |
| Python bridge contract | PASS | 4 of 4 passed, including the narrow icon resource declaration. |
| Extension build | PASS | `extension/dist/manifest.json` reports `0.2.0-rc19.dev1`; the icon exists in the output. |
| Live gateway smoke | PASS | Exactly eight tools were listed and one runtime status result was returned. |
| Updated loopback start | PASS | The rebuilt bridge listened on `127.0.0.1:3007`. |

## Manual Retest Still Required

1. Reload the unpacked extension on `chrome://extensions`.
2. Reload ChatGPT or open a fresh ChatGPT conversation.
3. Verify the PLwC icon renders in both the launcher and panel header.
4. Verify `8 / 8 tools verified` and a connected bridge status.
5. Generate and insert a primer that reports `0.2.0-rc19.dev1`.
6. Request `plwc status` and verify one new `plwc_status` event call with
   `scope="runtime"` enters the queue.
7. Verify calls from the conversation before the reload do not enter the queue.
8. Leave the panel idle for more than 30 seconds and verify it remains connected.

The write/read, protected-path denial, and Governor confirmation acceptance
cases remain pending until this manual retest passes.
