# PLwC Chat Bridge Extension

Small Chrome Manifest V3 extension for the local PLwC Chat Bridge. It connects
ChatGPT to the loopback bridge at `ws://127.0.0.1:3007/message`, validates the
eight-tool PLwC facade, and mounts an isolated terminal-style control panel.

## Build

```powershell
npm install
npm run check
```

The unpacked extension is written to `dist/`. Load that directory through
Chrome's extension developer mode.

## Runtime Boundary

- The content script runs only on `chatgpt.com` and `chat.openai.com`.
- UI styles live in an open Shadow DOM attached to `document.documentElement`.
- The host page, its body, navigation, and composer styles are never changed.
- A PLwC icon beside the host composer toggles the panel without occupying the
  text input; the right-edge launcher remains a fallback.
- The WebSocket endpoint is fixed to IPv4 loopback.
- The production bundle embeds the canonical `build-identity.json`. A
  connection is accepted only when `build/identity` matches every expected
  field. The Status tab displays the common build ID and the separate Node
  Bridge, extension and native launcher versions.
- The panel requests the optional Windows native launcher
  (`plwc.chat_bridge.launcher`) when the local loopback bridge is offline; the
  Status tab `Reconnect` button repeats the request manually. PLwC Setup
  registers it for the selected browser; the compiled bridge setup helper can
  repair the registration without requiring a script.
- The Settings tab edits the shared PLwC bootstrap values. The profile field is
  only a fallback when no governed profile state exists. `Save & Restart`
  writes shared PLwC and installed Claude MCPB settings before restarting and
  verifying the managed gateway child; it never overwrites
  `active_profile.json`. Imported values remain restorable.
- While a PLwC call is running, the ChatGPT input remains locked through result
  validation and automatic result submission. Settings exposes a maximum input
  lock from 0 to 60 seconds (60 by default; 0 disables locking), and the visible
  `Unlock input` control always releases the composer without cancelling the
  running PLwC operation.
- Tool execution is enabled only after `tools/list` returns the exact canonical
  eight-tool contract.
- Visible ChatGPT `plwc_tool_call` wrapper calls are deduplicated and queued in
  the `Status` tab.
- Calls already visible when the extension loads are treated as the session
  baseline and are not queued for execution.
- The generated primer uses the same `plwc_tool_call` wrapper protocol enforced
  by the parser.
- When an operation schema or argument shape is unclear, the Primer requires a
  precise `plwc_describe` call, uses operation filters for workspace and
  document operations, and forbids guessed operation names or arguments.
- The primer renders one shared workspace policy in English and German:
  required intermediate artifacts stay under `Temp/<task-name>/`, final
  results use the user-requested target, `Temp/` is never cleaned
  automatically, workspace content is never deleted, explicit deletion
  requests may be offered as confirmed moves to `Trashcan/`, and `Inbox/` is
  never created or used.
- A 20-second loopback ping keeps an active MV3 WebSocket session alive.
- The content script reconnects every 15 seconds when the browser has restarted
  the service worker and reloads the eight-tool contract before execution
  resumes.
- A tool request arriving before that refresh reloads and validates the same
  contract synchronously before it can execute.
- MCP result envelopes are normalized once and remain lossless. Results above
  the inline transport budget use `plwc_result_chunks.v1`, including ordered
  chunks, per-chunk hashes, a whole-result hash and explicit completeness
  metadata. Chunked envelopes are serialized compactly to reduce host-editor
  work; only formatting whitespace is removed and the complete result remains
  reconstructable and validated.
- Approved `profile_creation` plan results carry a strictly validated
  `plwc_onboarding_continuation.v1` block. It contains the complete correlated
  Governor apply wrapper for use after explicit user confirmation. Successful
  applies carry the exact read-only runtime-status verification wrapper.
- Chain recovery recognizes a response that claims PLwC execution is not
  possible even though work remains. It resubmits the verified continuation
  context, keeps `plwc_governor` distinct from `plwc_describe`, and leaves the
  normal write-confirmation boundary intact.
- Collapsed ChatGPT reasoning disclosures in the newest assistant turn are
  revealed once so fenced PLwC calls can mount. Tool discovery and recovery
  also reconcile periodically instead of relying exclusively on DOM mutation
  events; a raw call marker or a still-collapsed reasoning disclosure blocks
  premature recovery.
- Result cards distinguish `Policy denied`, `Validation failed`, `Not found`,
  `Unavailable`, `Gateway failed`, and `Transport failed`. Artifact-producing
  results expose origin and validation metadata; unvalidated artifacts carry an
  explicit warning and are never presented as safe.
- Startup and every ChatGPT conversation change establish a quiet hydration
  baseline. Tool-call JSON and chain-recovery text already present in an old
  chat are never treated as new automatic work.
- Policy-approved read-only results are inserted and submitted automatically
  when the composer contains no user draft.
- Mutating and unknown operations require explicit confirmation by default.
  Separate default-off settings may automate recognized writes and sandbox
  calls, each with a red warning; unknown operations remain manual, and
  confirmed Governor calls are forwarded with `confirmed=true`.
- A collapsed call that still needs individual confirmation shows `! CONFIRM`
  in its compact header.

The source icon is copied unchanged from the repository root during setup and
referenced for every Chrome manifest icon size.
