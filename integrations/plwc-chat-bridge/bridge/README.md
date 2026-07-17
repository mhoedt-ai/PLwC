# PLwC Chat Bridge: loopback server

This package is the local WebSocket-to-MCP bridge for PLwC Chat Bridge. It is
an ESM TypeScript application for Node.js 22 or newer. It starts one
`plwc-gateway` stdio process through the MCP SDK and never restarts or retries a
tool call automatically.

## Security boundary

- The listener accepts only `127.0.0.1` as its configured host.
- WebSocket handshakes require a Chrome extension origin; ordinary web pages
  cannot call the loopback bridge directly.
- The gateway must advertise exactly the eight canonical PLwC facade tools.
- The tool contract is checked at startup and again before every tool call.
- Unknown, missing or duplicate tools fail closed.
- WebSocket requests require JSON-RPC 2.0 and non-negative numeric IDs.
- Only `ping`, `tools/list` and `tools/call` are exposed.
- Gateway and configuration errors returned to clients are bounded and never
  contain command lines, environment values or local paths.

The JavaScript MCP SDK names its client-session class `Client`. This package
wraps that class and `StdioClientTransport` in `GatewayClientSession` so that
one bridge instance owns exactly one stdio session and child process.

## Configuration

Start the bridge with an explicit JSON configuration:

```powershell
npm start -- --config ..\config\plwc.local.json
```

Only the following fields are consumed:

```json
{
  "bridge": {
    "host": "127.0.0.1",
    "port": 3007,
    "path": "/message"
  },
  "gateway": {
    "command": "plwc-gateway",
    "args": [],
    "cwd": "${repoRoot}",
    "env": {
      "PLWC_CONFIG_FILE": "${PLWC_CONFIG_FILE}"
    }
  }
}
```

`${configDir}` and `${repoRoot}` are built-in substitutions. Other placeholders
are read from the bridge process environment. An unresolved placeholder makes
configuration loading fail.

## Development

All versions are exact. The runtime pins are
`@modelcontextprotocol/sdk@1.29.0` and `ws@8.21.1`; both supersede
prototype-era versions affected by npm security advisories.

```powershell
npm install
npm test
npm start -- --config <config.json>
```

`npm test` builds the TypeScript sources, then runs the focused Node test suite.
