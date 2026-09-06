# Permission, Host Access, and Data-Use Inventory

Product version: `1.0.0`

This inventory is evidence for the Chrome Web Store and Microsoft Edge Add-ons
forms. It describes the checked source tree; it is not aspirational copy.

## Single purpose

Connect the ChatGPT web interface to a separately installed, local PLwC
governance gateway so users can inspect, approve, execute, and return results
from the gateway's eight controlled tools.

The panel, primer, result rendering, local settings, native launcher request,
and loopback transport all serve that one purpose.

## Manifest access

| Declaration | Exact scope | Why it is required | Code evidence |
| --- | --- | --- | --- |
| `storage` | Extension-local browser storage only; no sync storage | Retains bridge automation preferences, local PLwC configuration overrides, and the bounded exactly-once registry across service-worker/browser restarts. | `src/background/index.ts` (`getSettings`, `savedGatewaySettings`, `claimPersistedToolCall`) |
| `nativeMessaging` | Host name `plwc.chat_bridge.launcher` | Requests the Setup-installed native launcher to start and verify the local loopback Bridge when it is unavailable. The Store cannot install the native host. | `src/background/index.ts` (`requestNativeBridgeStart`), `src/background/native-launcher.ts` |
| `host_permissions` | `ws://127.0.0.1:3007/*` | Connects only to the PLwC loopback JSON-RPC Bridge. There is no wildcard, LAN, Internet, `http`, or `https` network permission. | `src/shared/contracts.ts` (`BRIDGE_ENDPOINT`), `src/background/transport.ts` |
| content-script match | `https://chatgpt.com/*` | Finds explicit PLwC tool-call/result protocol blocks, mounts the visible panel, and inserts user-visible primer/results on the supported ChatGPT host. | `src/content/index.ts`, `src/content/tool-call-observer.ts`, `src/content/composer.ts`, `src/panel/plwc-panel.ts` |
| content-script match | `https://chat.openai.com/*` | Retains compatibility with the legacy official ChatGPT host for the same purpose and no additional behavior. | Same content-script sources and the `ALLOWED_HOSTS` guard in `src/content/index.ts` |
| web-accessible resource | PLwC icon on the two ChatGPT hosts | Lets the injected panel and composer launcher display the packaged PLwC icon. No script, HTML, user data, or configuration is web-accessible. | `src/manifest.json`, `src/panel/plwc-panel.ts` |
| background service worker | Packaged `background.js`, ES module | Owns browser storage, exact loopback transport, build-identity validation, permission enforcement, and native-launcher calls. | `src/background/index.ts` |

The toolbar `action` declares a title and icon but no popup and no additional
permission. The icon is packaged locally.

## Extension identity and Native Messaging boundary

The canonical runtime contract permits exactly these origins and no wildcard:

| Identity | Classification | Native Messaging origin |
| --- | --- | --- |
| `nlogfcafjdfdoknpkbehjgihpafpipdb` | Development/sideload only | `chrome-extension://nlogfcafjdfdoknpkbehjgihpafpipdb/` |
| `feceodobnhefdbfgmbinkndhogpfkicb` | Chrome Web Store; also the Chrome Store package tested in Brave | `chrome-extension://feceodobnhefdbfgmbinkndhogpfkicb/` |
| `nncomjknhhlgcmkmlaljhkiojcnpmflb` | Microsoft Edge Add-ons | `chrome-extension://nncomjknhhlgcmkmlaljhkiojcnpmflb/` |

The loopback WebSocket boundary accepts the corresponding Origin header values
without the trailing slash. A web page, an unapproved extension ID, an omitted
origin, and a wildcard are rejected. The Native Launcher verifies bridge health
through all three approved WebSocket origins before it reports the local
eight-tool contract as ready.

## Data handled

| Data | Source | Processing and destination | Persistence |
| --- | --- | --- | --- |
| Visible ChatGPT message text | DOM on the two matched hosts | Scanned locally for explicit PLwC call/result markers and narrowly defined chain-recovery conditions; relevant protocol payloads are rendered in the UI or passed to the local Bridge. No full transcript is sent to a publisher service. | Not persisted as a transcript by the extension. |
| PLwC tool names, arguments, results, errors, and confirmation state | Explicit PLwC protocol blocks and local Bridge responses | Validated and displayed; approved calls go to `127.0.0.1`; primer/results may be inserted into the ChatGPT composer and submitted according to visible settings or an explicit action. ChatGPT then processes submitted content under the user's ChatGPT relationship. | Tool arguments are included in the local exactly-once signature registry; result cards are held in page/service-worker memory. PLwC may persist user-requested output under its separate local governance rules. |
| ChatGPT conversation path and PLwC call ID | Current matched page URL and explicit call wrapper | Used to prevent duplicate execution and detect conflicting reuse of an ID. | Stored in `chrome.storage.local` in a bounded registry of at most 5,000 entries, together with timestamp and a deterministic payload signature. |
| Bridge behavior preferences | User controls in the panel | Applies local rendering, delay, confirmation, and submission behavior. | `chrome.storage.local` until changed, reset through browser data controls, or the extension is removed. |
| PLwC configuration overrides | User-entered workspace/profile paths, profile fallback, thresholds, and Boolean feature choices | Sent only to the local loopback Bridge; lets the user manage the separately installed local PLwC runtime. | `chrome.storage.local` until reset or removal; the local PLwC runtime retains its own settings separately. |
| Build identity, connection state, tool schemas, and launcher status | Packaged identity and local runtime | Validates that the Extension, Bridge, and Native Launcher belong to the accepted build and that exactly eight tools are exposed. | Primarily in service-worker/page memory. |
| Clipboard output | User-selected tool result | The extension writes a result only after the user chooses Copy Complete Result. | Managed by the operating system clipboard; the extension does not read clipboard content. |

## Store data-category answers

Use the exact labels offered by the live dashboard. Based on the official
definitions verified on 2026-08-09, the conservative answers are:

- Personal communications: handled. The extension inspects visible ChatGPT
  messages for PLwC protocol and recovery signals.
- Website content: handled. The extension reads the matched ChatGPT DOM and
  explicit protocol payloads required for its visible feature.
- Web history or browsing activity: handled in a narrow form. The current
  ChatGPT conversation path/domain is used for session identity and duplicate
  prevention; other browsing history is not accessed.
- User-generated content: handled where tool arguments, tool results, profile
  names, paths, or generated artifacts contain user content.
- Authentication information, financial/payment information, health
  information, and precise location: not intentionally requested, extracted,
  or classified. Users should not place sensitive content in PLwC tool calls.
  If such content is voluntarily included in a tool payload, it is handled as
  part of the disclosed website/personal-communication content, locally and in
  the submitted ChatGPT message.
- User-activity analytics: not collected. UI clicks are used to perform the
  requested action but are not logged for analytics or sent to the publisher.

## Collection, sharing, and Limited Use

- The publisher operates no analytics, advertising, telemetry, or extension
  backend and receives no extension runtime data automatically.
- Runtime data is not sold, used for advertising, creditworthiness, lending,
  or unrelated profiling.
- Data is used only to provide the visible local Chat Bridge feature.
- Data is not transferred to third parties by a publisher service. Content the
  extension inserts and submits into ChatGPT is sent through the existing
  ChatGPT page and is processed by OpenAI under the user's account and settings.
- Local tool calls go only to the fixed IPv4 loopback Bridge. Chrome's official
  User Data FAQ exempts same-computer native-program transfers from its secure
  transport requirement. The endpoint must remain loopback-only; it must never
  be widened to a network interface.
- Human access by the publisher occurs only if a user intentionally provides
  specific diagnostic material for support, or where required for security or
  law. Users are told to remove personal data and secrets from support reports.

## Remote code

Answer: **No, the extension does not use remote code.**

All extension JavaScript is built into the submitted package. There are no
remote script tags, remote module imports, `eval`, or downloaded executable
logic. JSON-RPC messages are data exchanged with the separately installed
local PLwC application; they are not fetched JavaScript or WebAssembly executed
by the extension.

## User controls and deletion

- Users can disable automatic read-only execution and automatic result
  submission. Write and sandbox automation are separate, default-off settings
  with visible warnings; unknown operations always require confirmation.
- Users can reset PLwC configuration overrides from the panel.
- Removing the extension clears browser-managed extension-local storage under
  normal Chrome/Edge behavior. Removing the extension does not delete the
  separately installed PLwC workspace, profiles, audit data, or native app.
- Users manage separately installed PLwC data through PLwC and Windows Setup.
  Support requests can be sent through the public support page without sending
  credentials or private workspace content.
