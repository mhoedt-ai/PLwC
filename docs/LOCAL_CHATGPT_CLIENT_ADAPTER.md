# V1-LOCAL-CHATGPT-ADAPTER-001: PLwC Chat Bridge

Status: **DESIGN / LOCAL PROTOTYPE**
Owner: **PLwC project**
Created: **2026-07-17**
Last updated: **2026-07-17**
Release target: **Proposed for the v0.2.0-rc19 development track; not part of v0.2.0-rc18.dev9**

This document is the project source of truth for **PLwC Chat Bridge**, the
proposed PLwC-owned local ChatGPT browser client integration. It records the
local proof of concept, the upstream-derived patches made during investigation,
the intended product boundary and the work required before this can become a
supported PLwC integration.

It is not an installation guide or a support claim for the current Open Beta.

## Naming Decision

The PLwC product name for this work is **PLwC Chat Bridge**.

The upstream MCP SuperAssistant project may be named only for source,
license, attribution and migration history. It must not be used as the
PLwC-facing product name, extension name, package name or support label.

The extension and launcher must use the existing PLwC Gateway icon from
`plwc-icon-512.png` as their product icon. Browser-required icon sizes may be
derived from that source asset, but they must preserve the PLwC Gateway visual
identity rather than introducing a new bridge-specific logo.

## Visual Design Direction

PLwC Chat Bridge should look like a restrained 1980s terminal interface:
black base surfaces, green phosphor text and sharp monospace UI. The design
should feel technical and local, but it must remain readable and usable for
long work sessions.

Required visual direction:

- primary surface: near-black, for example `#020403` or `#050806`;
- primary text and active signal: terminal green, for example `#5CFF7A`;
- secondary text: dim green, for example `#8FD99A`;
- borders and separators: dark green, for example `#123D1E`;
- warning state: muted amber; denial/error state: muted red, used sparingly so
  green/black remains the dominant identity;
- typography: monospace first, using bundled or system-safe terminal-like fonts
  such as `Cascadia Mono`, `Consolas`, `Courier New` and `monospace`;
- controls: compact, rectangular and sharp; avoid rounded marketing cards;
- iconography: use the PLwC Gateway icon as the header, browser action,
  extension-management and launcher icon;
- optional scanline, glow or cursor effects must be subtle, disabled for
  `prefers-reduced-motion`, and never reduce legibility.

The bridge UI should not imitate a full-screen toy terminal. It is a compact
tool panel inside an existing chat product, so density, clear state labels and
safe confirmation controls matter more than nostalgia.

## Host Chat Layout Requirement

The bridge must not hide, push away or make unreachable the host chat menu on
the left side. The prototype showed a failure mode where the running bridge
shifted the ChatGPT/MChat left navigation so the user could no longer reach
it. That is a release blocker for rc19.

Required layout behavior:

- prefer a right-side dock, popover or floating panel that does not alter the
  host application's left navigation geometry;
- if the bridge needs horizontal space, it must collapse itself before it
  overlaps or displaces the left chat menu;
- the user must always have a visible control to collapse, reopen and move the
  bridge panel;
- injected CSS must be namespaced or shadow-DOM isolated so it cannot leak into
  host navigation, chat list or composer styles;
- desktop, narrow desktop and mobile-width smoke tests must verify that the
  host chat menu remains reachable while the bridge is connected, disconnected
  and showing tool results.

## PLwC Interaction Model

The upstream-style generic prompt injection flow must become a PLwC-specific
session primer flow.

Required interaction model:

- rename the injected prompt surface to **Bridge Primer** or **Session Primer**;
- the primary action should use PLwC wording such as `Prime Chat` or
  `Insert Bridge Primer`, not generic upstream wording;
- generate the primer from the current eight public PLwC tool schemas instead
  of maintaining a stale hard-coded JSON mask;
- include the bridge/version line, local data-flow warning and execution policy
  in the primer;
- show compact human-readable tool summaries first, with raw JSON schema views
  available only in an advanced/details view;
- remove or heavily constrain generic custom instructions so they cannot become
  an unsupported policy bypass or unreviewed prompt layer;
- keep the primer versioned and reviewable so smoke evidence can show exactly
  what was inserted into the chat.

The visible panel should use PLwC-specific tabs rather than generic
SuperAssistant labels:

- `PLwC Tools`: list exactly the eight public facade tools and their current
  enabled/disabled state;
- `Primer`: show the versioned bridge primer, preview and insert action;
- `Policy`: show read-only automation, write confirmation and Governor apply
  confirmation rules;
- `Status`: show bridge, gateway, profile and transport diagnostics;
- `Settings`: keep only technical connection, theme and maintainer options.

## Decision

PLwC should own a dedicated local ChatGPT browser client adapter based on the
MIT-licensed MCP SuperAssistant project, provided the prototype can be reduced
to a maintainable, PLwC-specific distribution and passes the security and smoke
criteria in this document.

The adapter is a **client integration**, not a governed backend adapter. Its
eventual source belongs under a top-level integration boundary such as:

```text
integrations/plwc-chat-bridge/
```

It must not be placed in `src/plwc_gateway/adapters/`, because that package
contains policy-controlled execution adapters behind the PLwC gateway. The
browser extension and local transport proxy are host-side client components in
front of the gateway.

## User Requirement Captured By The Prototype

The target experience is:

- use the signed-in ChatGPT web UI and the user's ChatGPT subscription;
- do not require an OpenAI API account or API billing;
- let ChatGPT decide from normal language when a PLwC tool is needed;
- execute PLwC tools on the same local machine;
- keep the PLwC stdio gateway and all governed operations local;
- require no public port, Cloudflare tunnel, VPN or hosted MCP facade;
- expose only the eight public `plwc-gateway` facade tools;
- keep PLwC as the policy and governance authority.

The intended local route is separate from the hosted ChatGPT custom-app route
tracked by `V1-REMOTE-MCP-FACADE-001`.

## Target Architecture

```text
ChatGPT web UI and subscription model
  -> PLwC-specific browser extension
  -> loopback-only WebSocket MCP bridge
  -> PLwC stdio gateway
  -> PLwC policy, audit and governed adapters
  -> configured local workspace and profiles
```

Properties:

- the browser extension runs locally in the user's browser;
- the bridge listens only on `127.0.0.1`;
- the bridge starts exactly one `plwc-gateway` stdio child;
- no inbound internet route reaches the bridge or raw gateway;
- tool results are inserted back into the ChatGPT conversation by the
  extension;
- information inserted into the conversation is then visible to the hosted
  ChatGPT service, so the adapter must not imply that all model context remains
  local;
- PLwC policy denials remain authoritative and must be rendered without being
  rewritten as transport failures.

## Important Product Boundary

The adapter does not turn a ChatGPT subscription into a native model API. It
automates tool-call exchange inside the existing ChatGPT web application. This
is technically workable but depends on ChatGPT's page structure and may require
maintenance when that structure changes.

The supported product must therefore be described as a local browser client
adapter, not as an OpenAI API replacement and not as a hosted ChatGPT custom
app.

## Prototype Baseline

The proof of concept was built from:

| Component | Prototype baseline |
| --- | --- |
| Upstream project | `srbhptl39/MCP-SuperAssistant` |
| Upstream version | `v0.6.0` |
| Upstream commit | `c26168ee2c5708a3a65ef5afd88cda1a97c81734` |
| Upstream license | MIT; copyright and license notice must be preserved |
| Browser | Chromium-based browser with an unpacked extension |
| Local transport | WebSocket on loopback, prototype port `3007` |
| Proxy | `@srbhptl39/mcp-superassistant-proxy`, invoked through `npx` |
| PLwC process | Existing `server.py` started as an MCP stdio child |
| Prototype PLwC package | Installed `0.2.0-rc9` package |
| Current repository release | `0.2.0-rc18.dev9` |
| Proposed PLwC development track | `0.2.0-rc19.dev5` |

The PLwC version mismatch is intentional evidence recording, not an accepted
target state. Product work must replace the stale installed rc9 path with the
current build/package and rerun the complete smoke matrix.

The prototype currently invokes the proxy with an unpinned `@latest` version.
That is not acceptable for a supported integration. A release must pin or
vendor the bridge implementation and record its exact source and license.

## Prototype Results

Confirmed on 2026-07-17:

- the browser extension connected to a loopback WebSocket bridge;
- the bridge started the PLwC stdio server;
- `tools/list` returned all eight public PLwC tools;
- the sidebar displayed all eight tools;
- `plwc_status(scope="runtime")` returned `ok: true`;
- the configured active profile was present and valid;
- the PLwC gateway reported all eight tools registered;
- no Cloudflare tunnel or public connector was required;
- the obsolete native ChatGPT connector that referenced a temporary
  Cloudflare URL was removed from the test account.

Not yet confirmed after the final renderer patch:

- end-to-end workspace write from a fresh ChatGPT conversation;
- end-to-end read-after-write verification;
- risk-aware confirmation behavior for writes and Governor operations;
- survival across browser restart, extension reload and ChatGPT UI updates;
- compatibility with the current rc18.dev9 package.

The attempted `testgpt.txt` write did not reach the proxy before the final
renderer fix. The absent file was verified locally. This is recorded as a
client execution bug, not as a PLwC gateway failure.

## Investigation Record

### Transport Findings

1. A ChatGPT web custom app expects a remotely reachable HTTPS MCP endpoint;
   it cannot directly launch a local stdio server.
2. A local browser extension can mediate between ChatGPT web content and a
   loopback bridge without an OpenAI API call.
3. SSE and Streamable HTTP experiments connected inconsistently or returned
   incorrect routes in this setup. They are not part of the selected prototype.
4. WebSocket transport at a loopback `/message` endpoint successfully carried
   plain MCP JSON-RPC.
5. The proxy prefixes JSON-RPC IDs while routing and restores them through
   `parseInt()`. String request IDs therefore returned as `null`; numeric IDs
   are required unless the proxy is fixed.

### Browser And Extension Findings

1. Chrome Manifest V3 Content Security Policy blocked generated validator code
   that used `unsafe-eval` through the generic MCP SDK/AJV path.
2. Direct JSON-RPC `tools/list` and `tools/call` requests avoided that CSP path.
3. ChatGPT renders a visible response card and a hidden editor/CodeMirror copy
   of the same JSONL function call.
4. The hidden copy could retain a Run button while the visible card lost it.
5. The upstream replacement search recognized XML `<invoke>` calls but not the
   JSONL function-call format emitted in the tested ChatGPT UI.
6. The execution tracker marked calls as executed when they were merely
   scheduled. Failed automatic execution could therefore suppress all retries.
7. The ChatGPT toggle state manager hard-coded `autoExecute: false` instead of
   reading the persisted user preference.
8. Tool refresh could enter a loop while the server was connected but the UI
   still showed zero tools.
9. Extension reloads could invalidate the content-script context and crash the
   sidebar or popover without a local error boundary.

## Prototype Patch Inventory

The current local upstream-derived worktree contains uncommitted prototype
changes against MCP SuperAssistant `v0.6.0`. They must be migrated
intentionally, with tests, rather than copied as an opaque build artifact.

| Area | Files | Prototype change |
| --- | --- | --- |
| Branding and host coverage | `chrome-extension/manifest.ts` | Prototype used temporary PLwC branding and exact `chatgpt.com` and `chat.openai.com` host matches; rc19 work must rename the extension to `PLwC Chat Bridge`. |
| PLwC defaults | `chrome-extension/src/background/index.ts` | Defaulted to loopback WebSocket and migrated untouched upstream defaults to the PLwC endpoint. |
| CSP-safe JSON-RPC | `chrome-extension/src/background/index.ts` | Added direct WebSocket `tools/list` and `tools/call` paths that avoid generated schema validators. |
| Numeric request IDs | `background/index.ts`, `WebSocketTransport.ts` | Used numeric JSON-RPC IDs so the current proxy can restore routed responses. |
| WebSocket primitives | `WebSocketPlugin.ts`, `WebSocketTransport.ts` | Added direct request tracking, timeouts and direct resource/tool/prompt listing. |
| Tool payload compatibility | `pages/content/src/core/mcp-client.ts` | Accepted both array payloads and `{ tools: [...] }` broadcasts. |
| Tool enablement reactivity | `pages/content/src/hooks/useMcpCommunication.ts` | Included enabled-tool names in memo dependencies so the sidebar updates correctly. |
| Sidebar reliability | `Sidebar.tsx`, `SidebarManager.tsx` | Added bounded refresh, stopped zero-tool refresh loops and forced the PLwC prototype sidebar visible. |
| Extension reload handling | `components/common/ExtensionContextErrorBoundary.tsx` plus sidebar/adapter integration | Prevented extension-context invalidation from taking down React surfaces. |
| ChatGPT automation state | `plugins/adapters/chatgpt.adapter.ts` | Read persisted auto-insert, auto-submit and auto-execute preferences. |
| Function execution result | `renderer/components.ts` | Made the Run handler return actual success/failure so automatic execution can retry safely. |
| Duplicate card handling | `renderer/functionBlock.ts` | Preferred visible cards, recognized JSONL replacements, restored missing Run buttons and released failed execution reservations. |

The patched extension completed `pnpm base-build` successfully on 2026-07-17.
Successful compilation is not equivalent to the pending end-to-end write smoke.

## Security And Confirmation Requirements

The generic upstream Auto Execute switch is too broad to become the final PLwC
security model.

The PLwC-specific adapter must implement or explicitly document all of these
rules:

- PLwC policy remains the final allow/deny boundary;
- the bridge must bind to loopback only and reject remote interfaces;
- no raw PBA, filesystem or secondary MCP server may be exposed;
- only the eight PLwC facade tools may be advertised;
- tool arguments and results must be bounded in the UI and logs;
- secrets, profile contents and private local paths must not be written to
  public logs or issue reports;
- read-only calls may support optional automatic execution;
- workspace writes, document creation, sandbox execution and other mutating
  calls require a deliberate confirmation policy;
- `plwc_governor(operation="apply")` must never be silently auto-executed;
- an extension UI confirmation cannot replace PLwC's own confirmation and
  governance checks;
- reconnect and retry logic must be idempotent or must not repeat mutating
  calls after an ambiguous timeout;
- execution history must distinguish `scheduled`, `running`, `succeeded`,
  `denied`, `failed` and `unknown` states;
- the adapter must not claim that ChatGPT conversation content remains local.

## Proposed Repository Layout

```text
integrations/
  plwc-chat-bridge/
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

The integration should be independently buildable so the Python gateway does
not acquire Node.js as a runtime dependency. Node.js may remain a build-time or
bridge-launch requirement until a smaller pinned bridge is selected.

## Delivery Plan

### P0 - Preserve The Prototype

Status: **IN PROGRESS**

- [x] Record upstream version, commit and license.
- [x] Record local architecture and observed failures.
- [x] Record the complete prototype patch inventory.
- [x] Add this item to PLwC project documentation.
- [x] Assign the PLwC-owned working name `PLwC Chat Bridge`.
- [ ] Commit the prototype changes on a named branch in an owned fork.
- [ ] Export a reviewable patch series from upstream `v0.6.0`.

### P1 - Establish The PLwC Client Integration Boundary

Status: **COMPLETE**

- [x] Create `integrations/plwc-chat-bridge/`.
- [x] Decide whether to vendor a reduced fork or build a smaller adapter from
  extracted MIT components.
- [x] Pin the bridge version or move bridge behavior into PLwC-owned code.
- [x] Add a machine-neutral example configuration scaffold.
- [x] Add a Windows launcher for the pinned PLwC-owned bridge.
- [x] Launch the current PLwC package, not a stale installed rc9 path.
- [x] Preserve upstream copyright, MIT license and source attribution.

### P2 - Make The Adapter PLwC-Specific

Status: **COMPLETE (IMPLEMENTATION)**

- [x] Remove unrelated providers, generic MCP presets and unsupported sites.
- [x] Advertise and render only the eight public PLwC tools.
- [x] Provide PLwC descriptions and safe default prompts.
- [x] Replace generic prompt injection with the versioned PLwC Bridge Primer.
- [x] Replace generic tabs with `PLwC Tools`, `Primer`, `Policy`, `Status` and
  `Settings`.
- [x] Add a PLwC connection/status panel with actionable local diagnostics.
- [x] Apply the PLwC Chat Bridge terminal-inspired green/black UI design.
- [x] Use `plwc-icon-512.png` as the source icon for the extension, browser
  action and launcher assets.
- [x] Keep the host chat menu reachable while the bridge panel is open,
  collapsed, connected, disconnected and rendering tool results.
- [x] Replace broad Auto Execute with risk-aware execution controls.
- [x] Keep manual Run available whenever automatic execution is disabled or
  fails safely.

### P3 - Contract And Browser Testing

Status: **IN PROGRESS**

- [x] Unit-test JSONL parsing and visible/hidden duplicate card selection.
- [ ] Contract-test numeric IDs, timeouts and proxy response routing.
- [x] Contract-test all eight tool schemas against the current gateway build.
- [ ] Test connected-zero-tools, reconnect and extension-context invalidation.
- [ ] Test read-only, deny, write, sandbox and Governor plan/apply flows.
- [ ] Browser-test that the bridge UI does not hide or displace the host chat
  menu across desktop, narrow desktop and mobile-width viewports.
- [x] Run Playwright/Chromium fixture tests against desktop, 768 px and 390 px
  viewports; live ChatGPT DOM verification remains pending.
- [ ] Record the exact ChatGPT UI build/date used for each smoke run.

### P4 - Packaging And Documentation

Status: **IN PROGRESS**

- [ ] Produce a reproducible extension build with checksums.
- [x] Provide one launcher/config flow for Windows.
- [x] Document browser permissions and data-flow implications.
- [ ] Add troubleshooting that never recommends exposing the raw gateway.
- [ ] Update `docs/INSTALLATION.md` support status only after all acceptance
  criteria pass.

## Acceptance Criteria

The integration is not supportable until all criteria below are true:

1. A clean checkout produces the same extension and bridge artifacts.
2. No command uses an unpinned `@latest` dependency.
3. The bridge binds only to loopback by default and in smoke tests.
4. A current PLwC package starts through the adapter without private paths in
   committed configuration.
5. ChatGPT lists exactly eight PLwC tools.
6. A normal-language status request produces one `plwc_status` call and one
   visible result.
7. A user-confirmed workspace write creates exactly one expected file.
8. A read-after-write verifies content without duplicate execution.
9. A denied traversal/protected-path write stays denied and creates nothing.
10. A disconnected bridge produces a bounded local error, not an endless
    refresh loop.
11. Reloading the extension and ChatGPT page does not execute stale mutating
    calls.
12. Governor `apply` cannot run without the required explicit confirmation.
13. Browser and proxy logs contain no private profile data or absolute user
    paths in release evidence.
14. The build preserves all required MIT attribution.
15. The support matrix clearly distinguishes this local adapter from the
    hosted remote MCP facade.
16. The bridge UI follows the PLwC Chat Bridge green/black terminal design
    direction while remaining readable and accessible.
17. The running bridge never hides, displaces or blocks access to the host chat
    menu on the left side.
18. The extension and launcher use the PLwC Gateway icon derived from
    `plwc-icon-512.png`, with no unrelated upstream or generic assistant logo
    in PLwC-facing surfaces.
19. The generic prompt injection flow is replaced by a versioned PLwC Bridge
    Primer generated from the current public tool schemas.
20. PLwC-facing tabs and controls use PLwC-specific labels and do not expose
    generic custom-instruction surfaces as an unsupported policy layer.

## Open Decisions

- Reduced upstream fork versus a smaller PLwC-owned extension.
- Vendored bridge versus separately pinned proxy dependency.
- Chromium-only first release versus simultaneous Firefox support.
- Manual confirmation policy for each mutating PLwC operation.
- Distribution as an unpacked maintainer build, signed extension package or
  browser-store publication.
- Update and compatibility policy when ChatGPT changes its DOM or JSONL format.

## Next Action

Load the built `extension/dist/` as an unpacked Chrome extension, run it against
the live ChatGPT DOM with the PLwC-owned bridge, then record one status call and
one explicitly confirmed write/read round trip. The live smoke must also verify
that the left chat navigation keeps the same geometry while the panel opens and
closes.
