# PLwC Chat Bridge

Status: rc19 development scaffold.

PLwC Chat Bridge is the proposed PLwC-owned local browser client integration
for using the signed-in ChatGPT web UI with the local `plwc-gateway` MCP
server. It is a client-side bridge in front of the governed PLwC gateway, not a
new backend adapter and not an OpenAI API replacement.

This directory is the rc19 integration boundary. It intentionally starts as a
scaffold so the upstream-derived proof of concept can be imported, reviewed and
reduced without turning prototype files into a supported product by accident.

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

The extension and bridge implementation are not vendored yet. The launcher is
a safety scaffold and refuses to start an unpinned proxy. The next implementation
step is to commit the upstream-derived prototype patch series in an owned fork
or import a reduced PLwC-specific implementation into `extension/` and `bridge/`.

## First rc19 Acceptance Targets

1. ChatGPT lists exactly eight PLwC tools.
2. `plwc_status(scope="runtime")` returns one visible result.
3. One confirmed workspace write creates exactly one expected file.
4. Read-after-write verifies the content without duplicate execution.
5. A denied protected-path write remains denied and creates nothing.
6. Governor `apply` cannot run without explicit confirmation.
7. The bridge panel never blocks the host chat menu.
