# STORE-G0-01 Acceptance Record

Date: 2026-08-09

Status: **PASS — publisher access, live pages, and both draft identities verified**

The two publisher ownership checks, the two distinct unpublished Store
identities, and the public HTTPS pages were verified with real external state.
This pass does not authorize certification, submission, or publication.

## Scope

STORE-G0-01 prepares the publisher and draft-identity gate for distributing
the PLwC Chat Bridge browser extension through the Chrome Web Store and
Microsoft Edge Add-ons. It does not authorize certification, submission, or
publication. It does not change the accepted Gateway, Chat Bridge, Native
Launcher, or Windows Setup versions.

- Gateway: `0.2.0-rc18.dev10`
- Chat Bridge, extension, and Native Launcher: `0.2.0-rc19.dev20`
- Windows Setup: `installer-r20`
- Setup build ID:
  `plwc-windows-setup@0.2.0-rc18.dev10/installer-r20#sha256:ff3fdb880519e1a5a6c6e3b79129ff818d4cd14ced3a72ed8c76af63a613e804`

## Official requirement verification

The current requirements were checked on 2026-08-09 using only official
Google Chrome and Microsoft sources. The detailed source ledger is
`integrations/plwc-chat-bridge/extension/store/official-requirements.md`.

The verified requirements include:

- Chrome developer registration, one-time fee, agreement acceptance, verified
  contact email, two-step verification, official website ownership, item
  upload, privacy fields, least privilege, MV3 remote-code restrictions,
  listing assets, and deferred publication;
- Edge Partner Center enrollment with an MSA as Primary Owner, permanent
  account-type selection, company verification where applicable, agreement
  acceptance, ZIP upload, visibility, the current dedicated Privacy page,
  minimum permissions, software-dependency disclosure, listing assets, and
  certification notes;
- separate public Store identities and exact Native Messaging origins. The
  official Edge Native Messaging documentation explicitly warns that a
  published extension ID can differ from its sideload identity.

## Implemented internal artifacts

- Public-only identity and URL contract:
  `integrations/plwc-chat-bridge/extension/store/store-contract.json`
- Publisher and draft-ID checklist:
  `integrations/plwc-chat-bridge/extension/store/publisher-draft-id-checklist.md`
- Permission, host, data-use, retention, and Limited Use inventory:
  `integrations/plwc-chat-bridge/extension/store/permission-data-inventory.md`
- English listing copy, permission justifications, data declarations, reviewer
  instructions, and screenshot/promotional-asset plan:
  `integrations/plwc-chat-bridge/extension/store/listing-en.md`
- English static privacy page:
  `integrations/plwc-chat-bridge/extension/store/public/chat-bridge/privacy/index.html`
- English static support page:
  `integrations/plwc-chat-bridge/extension/store/public/chat-bridge/support/index.html`
- Shared public-page stylesheet:
  `integrations/plwc-chat-bridge/extension/store/public/chat-bridge/store-pages.css`
- Keyless draft-identity seed builder:
  `integrations/plwc-chat-bridge/extension/scripts/build-store-draft-seed.ps1`
- Static Store contract suite:
  `integrations/plwc-chat-bridge/extension/src/store/store-contract.test.ts`

No new hosting stack was introduced. The repository contained no website
deployment project or `.openai/hosting.json`; the prepared static files target
the existing `plwc.de` site.

## Manifest and data-use result

The current extension is Manifest V3 and requests only:

- `storage`;
- `nativeMessaging`;
- `ws://127.0.0.1:3007/*` host access;
- content-script and icon-resource access on `https://chatgpt.com/*` and
  `https://chat.openai.com/*`.

All extension JavaScript is packaged. No remote script, remote module,
`eval`, or downloaded executable-code path was found. The Store declarations
therefore answer that remote code is not used.

The conservative data declarations cover visible website content, personal
communications, user-generated tool inputs/results, the current ChatGPT
conversation path and call identity, browser-local settings, local PLwC
configuration overrides, and same-device tool transport. They do not claim
that local processing is outside Store privacy policy. The public policy also
discloses that text inserted or submitted into ChatGPT is processed by OpenAI
under the user's ChatGPT account and settings.

## Development and draft identity result

The retained manifest public key resolves to:

`nlogfcafjdfdoknpkbehjgihpafpipdb`

This value is classified only as `development_sideload_only` in the Store
contract and matches the current development Native Messaging origin. It is
not a Chrome or Edge Store ID.

The draft-seed builder runs the accepted extension build, removes the
development `key` from the staged manifest, excludes source maps and key-file
formats, validates `manifest.json` at the archive root, and produces a ZIP
whose name includes `DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT`.

Local seed produced for verification:

- Artifact:
  `integrations/plwc-chat-bridge/extension/store/out/PLwC-Chat-Bridge-0.2.0-rc19.dev20-DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT.zip`
- SHA-256:
  `17ad3d89ebc7df23522cca4c7757cf10ee8801d8a65fdc7f9c350dba50461151`
- Size: `273,324` bytes.
- Archive-root files: `manifest.json`, `background.js`, `content.js`, and
  `icons/plwc-icon-512.png`; `key` present: `false`.
- Repository state: ignored by `.gitignore`; not a release or submission
  artifact.

The seed is only for creating two unpublished items and obtaining their public
IDs. Final Store packages, final origins, Store-ID Native Messaging, repeated
browser/Bridge/launcher acceptance, and renewed H2 belong to `BRIDGE-P0-03`.

The Chrome upload created one unpublished item with the public extension ID:

`feceodobnhefdbfgmbinkndhogpfkicb`

Canonical future listing URL:

`https://chromewebstore.google.com/detail/plwc-chat-bridge/feceodobnhefdbfgmbinkndhogpfkicb`

The Chrome ID is a valid 32-letter public Store identity and differs from the
retained development/sideload ID. The item remains a draft and has not been
submitted for review or publication.

The Edge upload created one unpublished item with the public CRX ID:

`nncomjknhhlgcmkmlaljhkiojcnpmflb`

ID-based future listing route:

`https://microsoftedge.microsoft.com/addons/detail/nncomjknhhlgcmkmlaljhkiojcnpmflb`

Partner Center states that the actual listing URL will be available only once
the extension is published. The route above is therefore a future public
locator derived solely from the public CRX ID, not evidence of a live listing.
The final canonical URL must be verified during `STORE-P0-02`. The Edge ID is
valid, differs from both the Chrome Store ID and the development/sideload ID,
and the Edge item remains an unpublished draft.

## Automated verification

Command:

`npm run check`

Result:

- TypeScript typecheck: `PASS`;
- Extension and Store contract tests: `148 passed, 0 failed`;
- production extension build: `PASS`;
- Store-specific tests: `8 passed, 0 failed` within the full 148-test suite;
- high-confidence credential/private-key scan of new Store artifacts: `PASS`;
- exact development-key/ID derivation and separation: `PASS`;
- least-privilege manifest inventory alignment: `PASS`;
- no-remotely-hosted-code static contract: `PASS`;
- privacy/support page completeness and canonical-URL alignment: `PASS`;
- official-source domain restriction: `PASS`;
- listing, reviewer, dependency, and screenshot-plan contract: `PASS`.

The generated draft seed also completed its internal archive-root, key-removal,
source-map exclusion, prohibited-key-file, and SHA-256 checks.

## External gate matrix

| Acceptance criterion | Current result | Evidence required to close |
| --- | --- | --- |
| Chrome Web Store publisher ownership verified | `PASS (external)` | Enrollment, approved publisher name, contact verification, two-step verification, dashboard access, draft upload authority, and control of `plwc.de` through the official Search Console workflow were confirmed. Private evidence remains outside the repository. |
| Microsoft Edge Add-ons publisher ownership verified | `PASS (external)` | Enrolled Individual developer account, Edge workspace access, extension-management authority, and successful package upload were confirmed. Private evidence remains outside the repository. |
| Public privacy and support URLs reachable | `PASS (external)` | Both targets return the intended public content over stable HTTPS and redirect once to the canonical `www.plwc.de` host. |
| Unpublished Chrome item provides its final public identity | `PASS (external)` | The keyless seed created one unpublished Chrome item; its public ID and canonical future listing URL are recorded. |
| Unpublished Edge item provides its final public identity | `PASS (external)` | The keyless seed created one unpublished Edge item and exposed its public 32-letter CRX ID. The ID-based future listing route is recorded; Partner Center states that the actual listing URL is unavailable until publication. No Partner Center Product ID is recorded. |
| Development ID remains explicitly separate | `PASS (internal)` | Static identity contract and draft-seed key removal are green. Reconfirm after real Store IDs are entered. |
| No secrets or account/payment/recovery data checked in | `PASS for STORE-G0-01 changes` | New-artifact scan and manual diff review; repeat after Product Owner edits public IDs. |

## Live URL verification

Checked on 2026-08-09:

- `https://plwc.de/` returned `200` and redirected to the existing PLwC website
  at `https://www.plwc.de/`.
- `https://www.plwc.de/index.html#security` returned the existing public PLwC
  security overview with the local Gateway and workspace security model. The
  Store pages link to it as supplementary project information, not as a
  replacement for the extension-specific privacy policy.
- `https://plwc.de/chat-bridge/privacy/` returned `200` after one redirect to
  `https://www.plwc.de/chat-bridge/privacy/`; its title, privacy heading,
  Limited Use disclosure, security section, contact address, loopback
  disclosure, and PLwC security link were present.
- `https://plwc.de/chat-bridge/support/` returned `200` after one redirect to
  `https://www.plwc.de/chat-bridge/support/`; its title, support heading,
  Store/native-software boundary, `8/8` validation guidance, repair guidance,
  secret-handling warning, and PLwC security link were present.
- `https://www.plwc.de/chat-bridge/store-pages.css` returned `200` and retained
  the reviewed PLwC navy, white, cyan, and blue brand tokens.
- The public PLwC homepage returned `200` and contained footer links to both
  Chat Bridge pages.

Accordingly, both public-page statuses are `verified`. Together with both
publisher-access checks and both distinct draft Store IDs, this closes
STORE-G0-01 as `PASS` without submitting or publishing either item.

## Public-page visual verification

The prepared privacy and support pages were rendered in Microsoft Edge for
desktop review and with an exact `390 x 844` mobile device-metric override.
Both pages loaded completely, retained their intended titles and headings, and
showed no horizontal overflow at the mobile viewport. The live deployment also
serves the shared branded stylesheet from the intended public path.

## Closure and next boundary

The publisher enrollment, live public pages, keyless draft uploads, and both
public draft identities required by STORE-G0-01 are complete. The repository
contains no Partner Center Product ID, Seller ID, account identity, credential,
payment, or recovery material.

The next Store work belongs to `STORE-P0-02`: complete the listing and privacy
forms, prepare final assets, verify the actual Edge listing URL when Microsoft
makes it available, and separately decide whether to submit for certification.
Final identity-aware packaging and Native Messaging origins remain assigned to
`BRIDGE-P0-03`.

The verified `plwc.de` URL can be selected in the final Chrome item listing
during `STORE-P0-02` if the draft form requires unrelated listing fields before
it permits that optional item-level selection.

The formal STORE-G0-01 disposition is `PASS`. Submission, certification, and
publication remain explicitly unauthorized by this record.
