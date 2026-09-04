# PLwC Chat Bridge rc19.dev2 Settings And Composer Evidence

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: configuration parity and composer-launcher follow-up
- Environment: Windows PowerShell, Node.js, Python 3.12

## Scope

rc19.dev2 makes the enabled Claude PLwC configuration authoritative for normal
Windows bridge startup and exposes the same nine settings in the bridge panel:

1. workspace path
2. profiles path
3. active profile name
4. security configuration path
5. memory write threshold
6. persona write threshold
7. temperament write threshold
8. Qdrant enabled
9. persona layer disabled

The Settings tab is a read-only mirror. A dedicated `settings/get` loopback RPC
returns only those allowlisted values and a source label. Arbitrary process
environment values are neither returned by the bridge nor accepted by the
extension parser.

The PLwC Gateway icon is also mounted beside the ChatGPT composer as the primary
panel toggle. The existing right-edge launcher remains a fallback when the host
composer is unavailable. Desktop and narrow viewport geometry keep the button
outside the input and to the right of the host navigation.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Bridge build and tests | PASS | 11 of 11 passed, including settings allowlist and origin rejection. |
| Extension build and tests | PASS | 22 of 22 passed, including settings parsing and two composer-position tests. |
| Python bridge contract | PASS | 6 of 6 passed, including full MCPB import and the no-MCPB default path. |
| Browser fixture build | PASS | The rc19.dev2 desktop fixture compiled successfully. |
| Version consistency | PASS | Workspace, bridge, extension, manifest, primer and config report `0.2.0-rc19.dev2`. |

## Effective Local Configuration

The parameterless launcher imports the enabled Claude PLwC MCPB configuration.
The expected effective values for this machine are:

- workspace: `%USERPROFILE%\Claude_Arbeitsumgebung`
- active profile: `WasIstDas`
- memory/persona/temperament thresholds: `2` / `3` / `6`
- Qdrant enabled: `true`
- persona layer disabled: `true`
- profiles path and security config: PLwC defaults

## Live Loopback Verification

The rebuilt parameterless launcher started on `127.0.0.1:3007` and reported
the Claude PLwC MCPB file as its configuration source. A Chrome-extension-origin
WebSocket probe confirmed:

- `settings/get` returned exactly the nine expected rows and no unrelated
  environment values;
- workspace and active profile matched the configured values above;
- `plwc_status(scope="runtime")` completed successfully without the previous
  mapped-drive timeout;
- the gateway reported eight of eight public tools, profile `WasIstDas`, the
  configured `2` / `3` / `6` thresholds, and a disabled persona layer.

The local file fixture could not be opened in the in-app browser because that
browser blocks `file:` navigation. The automated layout and fixture-build
checks passed; visual confirmation remains part of the Chrome reload below.

## Manual Browser Retest

After reloading `extension/dist` in Chrome:

1. Confirm that the PLwC icon appears beside the ChatGPT composer and toggles
   the panel.
2. Confirm the left ChatGPT navigation remains reachable with the panel open.
3. Open Settings and verify all nine rows match the effective values above.
4. Confirm `8 / 8 tools verified` and run one runtime status call.

The existing write/read, protected-path denial, and Governor confirmation
acceptance cases remain pending until the live browser retest is recorded.
