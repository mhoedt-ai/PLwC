# PLwC Chat Bridge rc19.dev5 Editable Settings And Compact UI Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: live feedback requesting editable PLwC settings, a composer-shaped
  launcher, compact chat masks and optional automatic write confirmation
- Environment: Windows PowerShell, Chromium fixture, Node.js, Python 3.12

## rc19.dev5 Corrections

- The Settings tab exposes all nine supported PLwC gateway values as editable
  controls instead of a read-only snapshot.
- `Save & Restart` validates and persists the exact nine-field allowlist, then
  restarts only the managed PLwC Gateway child. The browser page and loopback
  WebSocket bridge stay in place.
- `Use Imported Settings` deletes the saved override and restores the values
  imported from Claude/launcher configuration.
- Paths must be absolute, thresholds must be nonnegative integers, boolean
  overrides must be `true`, `false` or the empty PLwC-default selection, and
  unknown fields are rejected.
- Automatic confirmation for recognized writes is a separate, default-off
  bridge setting. Sandbox and unknown operations remain manual.
  Its red warning explains that enabled calls can mutate workspace files,
  documents, profiles or persistent PLwC data without an individual click.
- Accepted Governor confirmation is forwarded as `confirmed=true`; PLwC tool
  schemas, protected-path rules and final allow/deny policy remain active.
- Chat call and result masks are collapsed by default. Their closed rows show
  only `PLwC-Gateway-Call` or `PLwC-Gateway-Result` plus an accessible expand
  control. Tool name, policy, status, arguments, result and raw JSON controls
  are available after expansion.
- The composer launcher is a centered 40 px circle matching the host composer
  controls and continues to preserve the left chat navigation area.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 12 of 12 passed, including settings update/reset RPC and strict validation. |
| Extension typecheck, tests and build | PASS | Typecheck passed; 33 of 33 tests passed; production build completed. |
| Python bridge contract | PASS | 6 of 6 passed. |
| Browser fixture build | PASS | Fixture rebuilt from rc19.dev5 sources. |
| Version consistency | PASS | Bridge, extension, manifest, shared contract, config and package metadata report `0.2.0-rc19.dev5`. |

## Browser Fixture Results

The fixture was served from IPv4 loopback and inspected at a 1280 x 720
desktop viewport with a 260 px host navigation column.

| Check | Result | Observation |
| --- | --- | --- |
| Compact masks | PASS | Both collapsed masks measured 43.6 px high and exposed only the generic gateway label plus expand control. |
| Expanded details | PASS | Expanding the call revealed `plwc_status`, `SCHEDULED`, read-only policy, arguments, `Run` and `Show JSON`. |
| Editable configuration | PASS | Nine enabled controls were present: four text paths/profile fields, three numeric thresholds and two boolean selects. |
| Save and restart flow | PASS | Changing memory threshold from `2` to `4` changed the source to `PLwC Chat Bridge saved settings`. |
| Imported reset | PASS | `Use Imported Settings` restored memory threshold `2` and source `Claude PLwC configuration`. |
| Automatic write option | PASS | Default was unchecked; interaction changed it to checked while the warning remained visible in `rgb(255, 102, 125)`. |
| Composer launcher | PASS | Computed width and height were 40 px and border radius was 50 percent. |
| Host layout | PASS | Navigation remained left 0/right 260; cards ended at x=876 and the open panel began at x=888. |

## Signed-in Chrome Follow-up

- A live ChatGPT measurement found the inner `#prompt-textarea` center at
  y=947.1 px and the rounded composer shell center at y=939.6 px. The old
  launcher center matched the inner field and therefore appeared 7.5 px too
  low.
- Launcher positioning now keeps the inner field's horizontal anchor but uses
  the rounded shell for vertical centering. A focused regression test covers
  shell selection and rejects a wider rounded ancestor.
- The three `Method not found.` messages were traced to a still-running older
  loopback bridge process. After restarting the managed bridge, a live
  extension-origin WebSocket probe returned all eight canonical tools and
  recognized `settings/update`; invalid input correctly returned JSON-RPC
  `-32602` instead of `-32601`.

## Security Notes

- Saved gateway settings contain only the nine public configuration values;
  arbitrary extension storage fields are not forwarded to the child process.
- Settings changes are serialized. A failed child restart rolls back to the
  prior effective settings and reports a generic public error.
- Automatic write confirmation is never enabled by migration or default.
- The loopback server still rejects ordinary web-page origins and exposes only
  the canonical eight-tool facade.

## Chrome Reload

1. Rebuild and reload `extension/dist` on `chrome://extensions`.
2. Reload ChatGPT and insert the newly generated rc19.dev5 Bridge Primer in a
   fresh conversation.
3. Confirm the compact gateway call opens and closes without raw `jsonl`
   chrome remaining visible.
4. Verify one harmless setting save/restart and then restore imported values.
5. Keep automatic write confirmation off for the normal smoke. Enable it only
   for a disposable write fixture after reviewing the red warning.

The fresh signed-in ChatGPT write/read round trip remains a separate manual
acceptance test because it may create or mutate real workspace data.
