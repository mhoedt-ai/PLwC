# PLwC Chat Bridge rc19.dev0 Test Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Commit under test: `87570624fc8f207f30f502aeca97e8e74c027aca`
- Environment: Windows PowerShell, Node.js `v24.15.0`, Python `3.12.10`

## Scope And Result

The build, automated tests, live gateway smoke, launcher dry run, and loopback
listener start passed. The fresh unpacked-extension test on the live ChatGPT DOM
and the mutating acceptance cases remain pending.

Overall result for the executed scope: **PASS WITH OPEN LIVE-UI FINDING**.

## Reproduction

Run from `integrations/plwc-chat-bridge` on the commit above:

```powershell
npm run install:packages
npm run check
npm --prefix bridge run smoke
.\scripts\start-windows.ps1 -DryRun -WorkspaceRoot <repository-root>
.\scripts\start-windows.ps1 -WorkspaceRoot <repository-root>
```

## Recorded Results

| Check | Result | Evidence |
| --- | --- | --- |
| Git synchronization | PASS | Local `HEAD` matched `origin/codex/plwc-chat-bridge-rc19`. |
| Dependency installation | PASS | Bridge: 99 packages audited; extension: 11 packages audited; zero reported vulnerabilities in both installs. |
| Bridge build | PASS | TypeScript compilation completed without errors. |
| Extension build | PASS | Manifest V3 output was written to `extension/dist/`. |
| Bridge automated tests | PASS | 10 of 10 tests passed. |
| Extension automated tests | PASS | 16 of 16 tests passed. |
| Live gateway smoke | PASS | The current repository gateway advertised exactly eight tools and returned one `plwc_status(scope="runtime")` result. |
| Launcher dry run | PASS | Configuration resolved, the bridge build existed, and the endpoint remained `ws://127.0.0.1:3007/message`. |
| Live loopback start | PASS | A listener was observed on `127.0.0.1:3007`; launcher output reported `PLwC Chat Bridge listening on ws://127.0.0.1:3007/message`. |

## Automated Coverage Observed

The bridge suite covered strict loopback configuration, repository-root
resolution, canonical eight-tool enforcement, numeric JSON-RPC IDs, one-time
mutating-call forwarding, and rejection of ordinary web-page origins.

The extension suite covered the eight canonical tool names, fail-closed JSONL
parsing, malformed and duplicate input rejection, deduplication, panel layout,
primer hashing, and confirmation policy for workspace writes and Governor
`apply`.

## Open Finding

The generated primer currently instructs ChatGPT to emit one direct JSON object
with `name` and `arguments`. The content parser intentionally accepts only the
event-based JSONL sequence using `function_call_start`, `parameter`, and
`function_call_end`; its tests explicitly reject direct objects.

Align the primer with the tested event-based parser before using the automatic
detected-call queue for the write/read acceptance run. Do not weaken the parser
to accept arbitrary direct JSON objects without a separate security review.

## Pending Acceptance

1. Load `extension/dist/` as a fresh unpacked Chrome extension.
2. Verify the live ChatGPT page reports `8 / 8 tools verified`.
3. Run and display one runtime status result from the panel.
4. Confirm one workspace write and verify exactly one file was created.
5. Read the file back and verify exact content without duplicate execution.
6. Verify a protected-path write is denied and creates nothing.
7. Verify Governor `apply` cannot run without explicit confirmation.
8. Verify the left ChatGPT navigation remains reachable throughout.
