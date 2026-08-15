# PLwC Chat Bridge Store Listing Material (English)

Prepared for Chrome Web Store and Microsoft Edge Add-ons.

Status: complete English form copy, static listing assets, and exact public
Setup reviewer artifact for the current multi-identity build. Do not submit
until five final Store-ID screenshots, live Chrome/Brave/Edge Native Messaging
acceptance, and renewed H2 handoff have been recorded.

## Product identity

- Name: `PLwC Chat Bridge`
- Manifest version: `1.0.0`
- Manifest version name: `1.0.0`
- Short description (manifest, 38 characters):

> Local PLwC gateway bridge for ChatGPT.

- Suggested category: select the current dashboard category closest to
  productivity/workflow tools. The Product Owner must use the categories
  offered by the live store UI rather than hard-coding a stale category.
- Homepage: `https://plwc.de/`
- Security overview: `https://www.plwc.de/index.html#security`
- Privacy policy: `https://plwc.de/chat-bridge/privacy/`
- Support: `https://plwc.de/chat-bridge/support/`
- Exact Windows Setup reviewer artifact:
  `https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r22/PLwC-Setup-1.0.0-installer-r22.exe`
- Setup SHA-256:
  `b4f34b6a42a19f060e0765c1be9ef82e39ea813cf46e97576e3fb5357576ab5a`
- Setup signing: explicit unsigned candidate; Windows may show an unknown-
  publisher warning.

## Detailed description

PLwC Chat Bridge connects the ChatGPT web interface to a separately installed,
local PLwC governance gateway. It adds a visible control panel to supported
ChatGPT pages so users can inspect the local connection, generate and insert the
Bridge primer, review structured PLwC tool calls, approve protected operations,
and return complete tool results to the conversation.

The extension works with the eight controlled tools exposed by the local PLwC
Gateway. It validates the exact tool set and common build identity before tool
execution is enabled. Read-only calls can run automatically after a configurable
delay. Recognized writes and sandbox calls require individual confirmation by
default, and unknown operations always require confirmation. Result cards retain
error class, provenance, validation state, and complete chunk metadata.

PLwC Chat Bridge is local companion software, not a hosted AI service. It does
not replace ChatGPT and does not provide a model. It has no publisher analytics,
advertising, telemetry, or cloud backend. It runs only on `chatgpt.com` and the
legacy official `chat.openai.com` host, and connects only to the PLwC Bridge at
IPv4 loopback address `127.0.0.1`.

Important dependency: installing this browser extension does not install PLwC,
the loopback Bridge, or the Native Launcher. Install the PLwC Windows Setup
package first. Browser installation always remains a separate Add/Get action
performed by the user.

The extension handles the visible ChatGPT content needed to recognize explicit
PLwC protocol blocks, the tool arguments and results selected for local
processing, a conversation/call identity used to prevent duplicate execution,
and local bridge settings. It sends approved tool calls only to the local PLwC
runtime. Primer and result text inserted or submitted into ChatGPT is processed
by OpenAI under the user's ChatGPT account and settings. See the privacy policy
for the complete data inventory, retention, controls, and Limited Use statement.

PLwC is in Open Beta and is not production-certified. Review confirmation
prompts and outputs before relying on them, and keep credentials and sensitive
content out of support reports.

## Single-purpose field

Connect the ChatGPT web interface to a separately installed, local PLwC
governance gateway so users can inspect, approve, execute, and return results
from the gateway's eight controlled tools.

## Permission justifications

### `storage`

Stores only extension-local bridge preferences, editable local PLwC
configuration overrides, and a bounded conversation/call registry used to
prevent duplicate tool execution across browser and service-worker restarts.
The extension does not use synchronized storage and does not send these values
to a publisher service.

### `nativeMessaging`

Contacts only the `plwc.chat_bridge.launcher` native host installed by PLwC
Windows Setup. When the fixed loopback Bridge is unavailable, this permission
lets the extension ask the local launcher to start and verify the matching PLwC
Bridge. The extension Store does not install the native application.

### Host permission `ws://127.0.0.1:3007/*`

Connects only to the separately installed PLwC JSON-RPC Bridge on IPv4
loopback. The scope cannot reach a LAN or Internet host and is required to list
and call the eight local PLwC tools and read local status/settings.

### Content-script hosts `https://chatgpt.com/*` and `https://chat.openai.com/*`

Runs the visible PLwC panel and explicit tool-call/result protocol only in the
current ChatGPT web application and its retained official legacy hostname. It
does not run on other websites or request access to all browsing activity.

### Web-accessible PLwC icon

Exposes only the packaged PLwC icon to the two supported ChatGPT hosts so the
panel and composer launcher can display it. No executable code, configuration,
or user data is exposed as a web-accessible resource.

## Remote-code field

Select: `No, I am not using remote code.`

Justification if a text field is shown: All JavaScript executed by the extension
is bundled in the uploaded Manifest V3 package. The extension has no remote
script, remote module, `eval`, or downloaded WebAssembly path. JSON-RPC messages
to the separately installed local PLwC application are data, not remotely
hosted extension code.

## Data-use disclosure

Select the live dashboard labels corresponding to:

- Personal communications
- Website content
- Web history/browsing activity, limited to the supported ChatGPT host and
  current conversation path used for duplicate prevention
- User-generated content, where represented separately by the dashboard

Do not select publisher analytics, advertising, sale of data, financial or
payment data, authentication data, health data, location, or user-activity
analytics. The extension does not intentionally request or classify those
categories.

Certify, consistently with the public privacy policy, that data is used only
for the single purpose, is not sold or used for advertising or lending, and is
not made available for unrelated human review. The publisher receives runtime
data only when a user intentionally supplies specific, sanitized support
material.

## Reviewer instructions

Use only the exact public Setup artifact and SHA-256 recorded above. Do not
replace that artifact binding with the generic releases page or with
credentials in Partner Center or in this repository.

### Chrome dashboard test instructions (500-character field)

> Windows 11: Download https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r22/PLwC-Setup-1.0.0-installer-r22.exe (unsigned; SHA-256 b4f34b6a42a19f060e0765c1be9ef82e39ea813cf46e97576e3fb5357576ab5a). Install with Chat Bridge selected. Add the extension, open chatgpt.com, then PLwC > Status > Reconnect. Expect 127.0.0.1, valid build and 8/8 tools. Primer inserts text; writes wait for confirmation. No PLwC credentials.

1. Test on Windows 11 with current Microsoft Edge or Google Chrome and a
   reviewer-controlled ChatGPT session. The extension has no PLwC account and
   requires no PLwC username, password, API key, or paid feature.
2. Install the exact PLwC Windows Setup package linked in the certification
   notes. Select the optional Chat Bridge component. Setup installs the local
   Gateway, loopback Bridge, and Native Launcher; the browser Store installs
   only the extension.
3. Complete the browser's normal Add/Get confirmation for the draft package.
   Do not sideload the retained development build when testing a Store ID.
4. Open `https://chatgpt.com/`. The PLwC icon appears beside the composer and at
   the right edge. Open the panel and select Status.
5. Choose Reconnect if needed. Expected result: the local endpoint is
   `ws://127.0.0.1:3007/message`, build identity is valid, and tool validation
   reports exactly `8/8` canonical tools.
6. In Primer, choose Generate and then Insert Bridge Primer. The text is placed
   visibly in the ChatGPT composer. Submit it using the reviewer's ChatGPT
   session.
7. Ask ChatGPT to check the PLwC runtime status. When an explicit
   `plwc_tool_call` block appears, the extension renders a PLwC call card. A
   read-only status call may run after the visible delay and its complete
   result is inserted/submitted according to the current setting.
8. Ask for a write operation or use a synthetic write call. Expected result:
   the operation does not run until its confirmation control is selected and
   Run is chosen. Sandbox automation and recognized-write automation are
   separate, default-off settings with red warnings. Unknown operations remain
   manual.
9. In Settings, verify that local paths and governance values can be read and
   edited, and that Use Imported Settings resets the extension override. Use
   only synthetic paths/profile names during certification.
10. Stop the local Bridge and choose Reconnect. Expected result: the extension
    asks the Setup-installed Native Launcher to start the matching local Bridge.
    If the native host is absent, the extension reports that the local companion
    is unavailable; it does not claim the Store can install native software.

When the native host is missing, the Status view states that the browser Store
installs only the extension and links to the official PLwC releases page. The
reviewer notes must still link the exact versioned Setup artifact tested for the
submission; the generic releases page is not a substitute for that artifact
binding.

Expected network boundary: extension code contacts no publisher server. Its
only extension-origin network connection is the fixed IPv4 loopback WebSocket.
Content inserted/submitted through the existing ChatGPT page is processed by
OpenAI as part of the reviewer's ChatGPT session.

## Screenshot and promotional-asset plan

Asset status: the static icon, Edge logo, and small promotional tile are ready
under `assets/` and recorded with dimensions and hashes in `assets/README.md`.
The five submission screenshots are intentionally pending until the final
packages have been loaded under their real Store identities with the exact
public Setup candidate. Local fixture or development-ID captures must not be
labeled as final Store evidence.

Capture all screenshots from the final Store-ID build on a clean Windows 11
test user with synthetic data. Do not show account email addresses, browser
profiles, API keys, private paths, real conversation content, publisher UI, or
payment information. Keep the extension and host-page UI legible and use full-
bleed browser captures without decorative Store badges.

Use five 1280 x 800 PNG screenshots so the same source set satisfies Chrome
and Edge:

1. **Local status and exact tool contract** — panel open on Status; valid common
   build identity, loopback endpoint, and `8/8` tools visible.
2. **Primer workflow** — Primer tab with Generate and Insert Bridge Primer;
   synthetic composer content and the manual user submission boundary visible.
3. **Protected tool call** — a PLwC call card awaiting confirmation, with the
   operation and warning readable and no sensitive arguments.
4. **Complete governed result** — a successful synthetic result card showing
   result class, provenance/validation metadata, and Insert/Copy controls.
5. **Local settings and safety controls** — Settings tab with synthetic paths,
   default-off write/sandbox automation, and the red warnings visible.

Ready static assets:

- Chrome store icon: `assets/plwc-chat-bridge-icon-128.png`.
- Edge logo: `assets/plwc-chat-bridge-edge-logo-300.png`.
- Small promotional tile (440 x 280 PNG):
  `assets/plwc-chat-bridge-small-promo-440x280.png`, using the concise line
  `Local governance bridge for ChatGPT` without Store ranking or certification
  claims.

Optional asset not currently required:

- Optional Chrome marquee / Edge large tile: 1400 x 560 PNG using the same
  branding and no screenshot collage.
- Edge allows a sixth screenshot; leave it unused unless certification needs a
  dedicated missing-native-host state.
