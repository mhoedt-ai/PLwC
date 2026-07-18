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
- The Settings tab edits all nine effective PLwC MCPB values, saves validated
  overrides, restarts the managed gateway child and restores imported values.
- Tool execution is enabled only after `tools/list` returns the exact canonical
  eight-tool contract.
- Visible ChatGPT JSONL calls are deduplicated and queued in the `Status` tab.
- Calls already visible when the extension loads are treated as the session
  baseline and are not queued for execution.
- The generated primer uses the same event-based JSONL protocol enforced by the
  parser.
- A 20-second loopback ping keeps an active MV3 WebSocket session alive.
- The content script reconnects every 15 seconds when Chrome has restarted the
  service worker and reloads the eight-tool contract before execution resumes.
- A tool request arriving before that refresh reloads and validates the same
  contract synchronously before it can execute.
- MCP result envelopes are normalized once; runtime status views and inserted
  results omit duplicated profile diagnostics and escaped JSON copies.
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
