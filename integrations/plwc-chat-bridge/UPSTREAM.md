# Upstream Attribution

PLwC Chat Bridge is a PLwC-owned integration. The current proof of concept was
based on the MIT-licensed MCP SuperAssistant project, but PLwC-facing product
surfaces must not use that name or icon.

## Recorded Baseline

| Field | Value |
| --- | --- |
| Upstream repository | `https://github.com/srbhptl39/MCP-SuperAssistant` |
| Upstream version | `v0.6.0` |
| Upstream commit | `c26168ee2c5708a3a65ef5afd88cda1a97c81734` |
| Upstream license | MIT |
| License source | `https://raw.githubusercontent.com/srbhptl39/MCP-SuperAssistant/c26168ee2c5708a3a65ef5afd88cda1a97c81734/LICENSE` |
| Proxy package used in prototype | `@srbhptl39/mcp-superassistant-proxy` |

## Migration Rules

- Preserve upstream copyright and MIT license text for any reused code.
- Keep upstream names only in attribution, license and migration history.
- Remove unrelated providers, generic MCP presets and unsupported host sites.
- Replace generic prompt injection with the PLwC Bridge Primer.
- Replace upstream extension branding with `PLwC Chat Bridge`.
- Use the PLwC Gateway icon derived from `../../plwc-icon-512.png`.
- Pin or vendor all bridge/proxy dependencies before any supported smoke.
- Do not ship any command that uses an unpinned `@latest` dependency.

## Review Boundary

Prototype patches must be imported as a reviewable patch series or as a reduced
PLwC implementation. Do not copy an opaque built extension into this directory
as the supported source of truth.

The PLwC-owned loopback bridge does not ship the prototype proxy package. Its
direct runtime dependencies are pinned to `@modelcontextprotocol/sdk@1.29.0`
and `ws@8.21.1`; older prototype pins remain investigation history only.
