# PLwC Chat Bridge

Status: rc19.dev1 implementation prototype.

PLwC Chat Bridge is the proposed PLwC-owned local browser client integration
for using the signed-in ChatGPT web UI with the local `plwc-gateway` MCP
server. It is a client-side bridge in front of the governed PLwC gateway, not a
new backend adapter and not an OpenAI API replacement.

This directory is the rc19 integration boundary. It contains a reduced,
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
- Policy: writes and Governor `apply` require deliberate confirmation.

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
- `scripts/start-windows.ps1` starts the built bridge with the example config.
- the live smoke starts the current repository gateway, lists eight tools and
  calls `plwc_status(scope="runtime")` once;
- the browser fixture verifies desktop, 768 px and 390 px panel geometry;
- npm lockfiles are committed and both runtime package audits report zero known
  vulnerabilities.

Recorded test execution:

- [rc19.dev0 test evidence, 2026-07-18](tests/RC19_DEV0_TEST_EVIDENCE_2026-07-18.md)
- [rc19.dev1 live-fix evidence, 2026-07-18](tests/RC19_DEV1_LIVE_FIX_EVIDENCE_2026-07-18.md)

This is still an rc19 development prototype. It has not yet completed a fresh
unpacked-extension smoke on the live ChatGPT DOM or a confirmed write/read
round trip.

## Build And Run

```powershell
cd integrations\plwc-chat-bridge
npm run install:packages
npm run check
.\scripts\start-windows.ps1 -DryRun
.\scripts\start-windows.ps1
```

Load `extension/dist/` as an unpacked Chrome extension after the build.

## First rc19 Acceptance Targets

1. ChatGPT lists exactly eight PLwC tools.
2. `plwc_status(scope="runtime")` returns one visible result.
3. One confirmed workspace write creates exactly one expected file.
4. Read-after-write verifies the content without duplicate execution.
5. A denied protected-path write remains denied and creates nothing.
6. Governor `apply` cannot run without explicit confirmation.
7. The bridge panel never blocks the host chat menu.
