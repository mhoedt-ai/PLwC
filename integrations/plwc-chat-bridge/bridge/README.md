# Bridge Source Boundary

This directory will hold the local loopback bridge source once the bridge is
pinned, vendored or reimplemented under PLwC ownership.

## Required Runtime Behavior

- Bind only to `127.0.0.1` by default.
- Start exactly one `plwc-gateway` stdio child.
- Advertise only the eight public PLwC facade tools.
- Preserve PLwC policy denials as policy denials, not transport failures.
- Do not retry mutating calls after an ambiguous timeout.
- Do not expose raw PBA, filesystem or secondary MCP servers.

The rc19 scaffold deliberately does not start the prototype proxy because the
prototype used an unpinned package path.
