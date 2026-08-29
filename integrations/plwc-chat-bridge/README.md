# PLwC Chat Bridge

Status: 1.0.0 implementation and local Store-origin readiness pass. The current
Windows r24 artifact is explicitly unsigned. Chrome is a private draft with an
approved trusted tester and Edge is a hidden draft; external Store-signed
identity acceptance remains on hold until their separate review gates pass.

PLwC Chat Bridge is the PLwC-owned local browser client integration
for using the signed-in ChatGPT web UI with the local `plwc-gateway` MCP
server. It is a client-side bridge in front of the governed PLwC gateway, not a
new backend adapter and not an OpenAI API replacement.

This directory is the 1.0 integration boundary. It contains a reduced,
PLwC-owned implementation informed by the upstream MIT prototype without
shipping the generic upstream extension or proxy package.

## Product Rules

- Product name: `PLwC Chat Bridge`.
- Product icon: derive browser and launcher icons from `../../plwc-icon-512.png`.
- Product UI: restrained black/green terminal style with monospace text.
- Host UI: never hide, push away or block the host chat menu on the left side.
- Transport: loopback only, defaulting to `127.0.0.1`.
- Gateway: start exactly one `plwc-gateway` stdio child.
- Tools: advertise only the eight public `plwc-gateway` facade tools.
- Primer: replace generic prompt injection with a versioned PLwC Bridge Primer.
- Policy: writes, Governor `apply` and sandbox execution require confirmation
  by default; separate warned standing-confirmation options may automate known
  writes and sandbox calls, while unknown operations stay manual.

## Directory Layout

```text
integrations/plwc-chat-bridge/
  README.md
  UPSTREAM.md
  LICENSES/
    MCP-SuperAssistant-MIT.txt
  extension/
  bridge/
  config/
    plwc.example.json
  scripts/
    start-windows.ps1
  tests/
    contract/
    browser/
    smoke/
```

## Current State

- `bridge/` contains the pinned Node.js WebSocket-to-MCP stdio bridge.
- `extension/` contains the PLwC-only Manifest V3 extension and Shadow DOM UI.
- the panel can be toggled from the PLwC icon beside the ChatGPT composer;
- the Settings tab edits and validates the shared PLwC bootstrap fields,
  persists one shared configuration and the Claude MCPB mirror, verifies the
  restarted managed gateway child, and can restore imported Claude/launcher
  values without overwriting governed active-profile state;
- the content script restores the loopback connection and eight-tool contract
  after a Chrome service-worker restart;
- MCP envelopes are normalized once without dropping runtime-status or sandbox
  fields;
- complete tool results, including full compiled profile layers, are returned
  to ChatGPT without bridge-side truncation; oversized general results use the
  lossless `plwc_result_chunks.v1` protocol with ordered chunks and SHA-256
  completeness metadata, while only expanded visual details are display-bounded;
  chunked envelopes use compact JSON without removing semantic content;
- an approved `profile_creation` Governor plan adds a validated
  `plwc_onboarding_continuation.v1` block to its correlated result. The block
  preserves the complete reviewed onboarding arguments and supplies exactly
  one `plwc_governor` apply call for use after explicit confirmation; a
  successful apply supplies exactly one read-only runtime-status verification
  call;
- chain recovery recognizes both missing-result claims and ChatGPT execution
  refusals. When a verified onboarding continuation exists, recovery repeats
  its exact wrapper and forbids substituting `plwc_describe`; it never executes
  the mutating continuation or bypasses the existing confirmation gate;
- visible PLwC wrapper calls and marked JSON results are replaced by compact,
  collapsed terminal rows; details and `Show JSON` are available on demand;
- startup and ChatGPT conversation changes establish a quiet hydration
  baseline, so historical call JSON and stale chain-recovery text in old chats
  are not treated as new automatic work;
- collapsed reasoning disclosures in the newest assistant turn are revealed
  once and both call observation and recovery have periodic reconciliation,
  so a deferred PLwC wrapper no longer depends on manual expansion;
- policy-approved read-only calls run automatically by default and their
  results are inserted and submitted through the ChatGPT composer;
- workspace inventory and content-search hits are treated as unverified path
  candidates until a real directory listing and exact `file_info` result prove
  the file exists; dependent calls from one GPT response execute serially;
- structured `ok=false` and policy denials render as failed or denied instead
  of being mislabeled as successful merely because the MCP envelope completed;
- mutating calls require explicit confirmation by default; separate default-off
  automatic confirmation options cover recognized writes and sandbox calls,
  each with a red warning, while unknown operations stay manual;
- collapsed calls that still require an individual confirmation show a visible
  `! CONFIRM` state instead of looking stalled behind long JSON details;
- `scripts/start-windows.ps1` imports the enabled Claude PLwC MCPB settings and
  starts the built bridge with the example config;
- `native/bin/plwc-chat-bridge-launcher.exe` registers or repairs the Chrome,
  Edge and Brave native launcher so the panel can start and verify the local
  WebSocket bridge after a PC reboot; the Status tab `Reconnect` button remains
  the manual retry;
- `build-identity.json` defines one installer-addressable build ID for the Node
  Bridge, browser extension and native launcher. The common build and all three
  component versions advance together; all three runtimes report the same
  identity and reject a mismatched peer before tool execution;
- PLwC Setup creates a limited per-user scheduled task that starts the Bridge
  after every Windows sign-in, verifies the configured loopback endpoint and
  rolls back the prior task/settings if repair or upgrade fails;
- the live smoke starts the current repository gateway, lists eight tools and
  calls `plwc_status(scope="runtime")` once;
- the browser fixture verifies desktop, 768 px and 390 px panel geometry;
- npm lockfiles are committed and both runtime package audits report zero known
  vulnerabilities.

Recorded test execution:

- [rc19.dev0 test evidence, 2026-07-18](tests/RC19_DEV0_TEST_EVIDENCE_2026-07-18.md)
- [rc19.dev1 live-fix evidence, 2026-07-18](tests/RC19_DEV1_LIVE_FIX_EVIDENCE_2026-07-18.md)
- [rc19.dev2 settings and composer evidence, 2026-07-18](tests/RC19_DEV2_SETTINGS_AND_COMPOSER_EVIDENCE_2026-07-18.md)
- [rc19.dev3 connection and result evidence, 2026-07-18](tests/RC19_DEV3_CONNECTION_AND_RESULT_EVIDENCE_2026-07-18.md)
- [rc19.dev4 chat automation evidence, 2026-07-18](tests/RC19_DEV4_CHAT_AUTOMATION_EVIDENCE_2026-07-18.md)
- [rc19.dev5 editable settings and compact UI evidence, 2026-07-18](tests/RC19_DEV5_EDITABLE_SETTINGS_AND_COMPACT_UI_EVIDENCE_2026-07-18.md)
- [rc19.dev6 native auto-submit evidence, 2026-07-18](tests/RC19_DEV6_NATIVE_AUTO_SUBMIT_EVIDENCE_2026-07-18.md)
- [rc19.dev7 automation timing and retry evidence, 2026-07-18](tests/RC19_DEV7_AUTOMATION_TIMING_AND_RETRY_EVIDENCE_2026-07-18.md)
- [rc19.dev8 complete result transport evidence, 2026-07-18](tests/RC19_DEV8_COMPLETE_RESULT_TRANSPORT_EVIDENCE_2026-07-18.md)
- [rc19.dev9 workspace evidence and sequencing evidence, 2026-07-18](tests/RC19_DEV9_WORKSPACE_EVIDENCE_AND_SEQUENCING_2026-07-18.md)
- [rc19.dev10 sandbox automation and confirmation evidence, 2026-07-18](tests/RC19_DEV10_SANDBOX_AUTOMATION_AND_CONFIRMATION_EVIDENCE_2026-07-18.md)

The rc19.dev0 through rc19.dev10 records above remain historical implementation
evidence. The current component identity is 1.0.0. Automated extension tests,
installed r24 Bridge health, the eight-tool contract, Native Launcher status,
and live loopback health using both assigned Store origins pass. The remaining
external gate is installation and acceptance of the review-approved,
Store-signed Chrome and Edge packages under their real IDs.

## Build And Run

```powershell
cd integrations\plwc-chat-bridge
npm run install:packages
npm run check
.\scripts\start-windows.ps1 -DryRun
.\scripts\start-windows.ps1
```

For development and local pre-release acceptance only, load `extension/dist/`
as an unpacked Chrome, Edge or Brave extension after the build. Its manifest key
fixes the separate development ID to
`nlogfcafjdfdoknpkbehjgihpafpipdb`. PLwC Setup registers the native host
and Windows autostart automatically. For a developer repair build, invoke the
compiled helper directly:

```text
native\bin\plwc-chat-bridge-launcher.exe --register --browser all --lang de
```

Use `--browser chrome`, `edge`, `brave`, `both` or `all`. The canonical identity
contract already includes the retained development ID and the assigned Chrome
and Edge Store IDs. A repeated `--extension-id` argument may add an explicitly
approved identity without removing the canonical origins. An unpacked build
must never be reported as Store-ID acceptance evidence.

On Windows, the launcher initially imports the enabled PLwC configuration at
`%APPDATA%\Claude\Claude Extensions Settings\local.mcpb.plwc.plwc-gateway.json`.
After the first `Save & Restart`, all nine shared bootstrap values are held in
`%APPDATA%\PLwC\config\gateway-settings.json`. The profile field is only a
fallback when no governed state exists. Gateway calls resolve governed
`active_profile.json` state first, then shared settings, then host/extension
configuration and finally PLwC defaults. Only confirmed Governor profile
creation or activation flows may change the governed state; Settings save,
rollback and reset preserve it. Do not pass the source repository as
`-WorkspaceRoot` merely because the bridge code lives there, especially when
the repository is on a mapped network drive.

## Version 1.0 Acceptance Targets

1. ChatGPT lists exactly eight PLwC tools.
2. `plwc_status(scope="runtime")` returns one visible result.
3. One confirmed workspace write creates exactly one expected file.
4. Read-after-write verifies the content without duplicate execution.
5. A denied protected-path write remains denied and creates nothing.
6. With automatic write confirmation disabled, Governor `apply` cannot run
   without explicit confirmation.
7. With automatic sandbox confirmation disabled, sandbox calls display
   `! CONFIRM` and cannot run without explicit confirmation.
8. The bridge panel never blocks the host chat menu.
