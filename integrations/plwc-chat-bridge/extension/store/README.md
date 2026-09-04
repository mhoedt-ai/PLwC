# PLwC Chat Bridge Store Preparation

This directory contains the public-safe Store preparation and package contracts
for `STORE-G0-01` and `BRIDGE-P0-03`.

The artifacts are not authorization to submit or publish the extension. The
Product Owner retains responsibility for developer-account enrollment,
identity and company verification, agreements, fees, public-contact approval,
website deployment, draft-item creation, certification, and publication.

## Artifact index

- `official-requirements.md` records the official Chrome and Microsoft sources
  verified on 2026-08-15 and the requirements derived from them.
- `store-contract.json` is the public-only identity and URL contract. It must
  never contain account identifiers, credentials, tokens, payment data, or
  recovery material.
- `permission-data-inventory.md` maps every permission, host, and data-handling
  declaration to the current manifest and source code.
- `listing-en.md` contains English listing copy, privacy-field answers,
  permission justifications, reviewer instructions, and the screenshot plan.
- `publisher-draft-id-checklist.md` is the Product Owner handoff checklist.
- `submission-checklist.md` binds the exact draft identities, packages, assets,
  saved dashboard result, and remaining HOLD conditions without authorizing a
  review submission or publication.
- `assets/` contains the reviewed static listing graphics and their hashes.
- `public/chat-bridge/` contains the English privacy and support pages prepared
  for the existing `plwc.de` website.
- `../scripts/build-store-packages.ps1` creates the final-candidate
  Chrome/Brave and Edge ZIPs from one checked production build.
- `../scripts/test-store-packages.ps1` rebuilds the packages twice and verifies
  byte reproducibility, the four-entry allowlist, identity sidecars, hashes,
  development-key removal, source-map exclusion, and the secret scan.
- `../scripts/build-store-listing-assets.ps1` derives the static listing icon,
  Edge logo, and Chrome small promotional tile from the canonical PLwC icon.

## Public URL targets

- Privacy: `https://plwc.de/chat-bridge/privacy/`
- Support: `https://plwc.de/chat-bridge/support/`
- Exact unsigned Setup reviewer artifact:
  `https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r24/PLwC-Setup-1.0.0-installer-r24.exe`

Both URLs and the shared branded stylesheet were externally reverified over
HTTPS on 2026-08-15. The non-`www` targets redirect once to the canonical
`www.plwc.de` host and return the intended public, indexable content with a
successful status. Their Store-contract status is therefore `verified`.

The Setup URL is a non-final GitHub prerelease reviewer asset. An anonymous
download on 2026-08-29 reproduced the accepted 5,218,213-byte EXE, SHA-256
`b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0`,
and Authenticode status `NotSigned`. Windows may show an unknown-publisher
warning. Publishing this artifact does not authorize Store review or release.

## Saved Store draft state

On 2026-08-15, both existing public Store items accepted their bound version
`1.0.0` package. Their English listings, public URLs, privacy declarations,
permission justifications, and static listing graphics were saved as drafts.
Edge was re-read as `Version 1.0.0` and `In draft`; Chrome likewise remains an
unsubmitted saved draft. No review, certification, or publication was started.
The exact public-safe evidence is recorded in `submission-checklist.md`.

## Historical draft identity seed

The current source manifest contains a public development key which resolves to
the retained development/sideload ID. It must not be uploaded to either store
to establish the production identities.

The two unpublished items already exist and retain their bound public
identities. The following command remains only for reproducibility of the
historical identity-seed process; its output must not be uploaded again:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-store-draft-seed.ps1
```

The generated ZIP under `store/out/` removes only the development `key` and
source maps from the normal checked build. Its filename states
`DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT`. Upload the same keyless seed once to a new
Chrome Web Store item and once to a new Microsoft Edge Add-ons item, save both
as drafts, and do not submit them for review. Final, privacy-filtered,
identity-aware Store packages belong to `BRIDGE-P0-03`.

## BRIDGE-P0-03 Store packages

Run from the extension directory on Windows:

```powershell
npm run test:store:windows
npm run build:store:windows
npm run build:store:assets:windows
```

The builder creates these ignored local artifacts under `store/out/`:

- `PLwC-Chat-Bridge-<version>-chrome-brave-store.zip`;
- `PLwC-Chat-Bridge-<version>-edge-store.zip`;
- one adjacent `*-store-build-identity.json` for each target.

Each ZIP contains exactly `manifest.json`, `background.js`, `content.js`, and
`icons/plwc-icon-512.png`. `manifest.json` is at the archive root. The source
manifest's development `key`, source maps, repository contracts, source files,
credentials, and private material are absent. ZIP entry order and timestamps
are fixed, so identical source produces identical bytes.

The two ZIPs intentionally have identical runtime content. Store signing binds
that keyless content to different public item identities. The adjacent sidecars
bind each filename and SHA-256 to either the Chrome/Brave ID or the Edge ID.
They record the extension package version separately from the compatible shared
PLwC/Bridge release and build identity; they are evidence files and are not
included in the uploaded ZIP.

The canonical runtime identity contract is
`../../native/extension-identity.json`. It names the retained development ID,
Chrome Store ID, Edge Store ID, and exactly their three Native Messaging and
WebSocket origins. Arbitrary additional IDs and wildcards are rejected.

Building a package is not authority to upload, submit, certify, or publish it.
The final browser/native acceptance must use the real Store identities. Three
privacy-sanitized 1280 x 800 Store-candidate screenshots are prepared under
`assets/screenshots-draft/`; verify them once against the current 1.0 UI before
upload. They are not a substitute for live browser/native acceptance.

Only the two ZIP files are browser-dashboard upload candidates. Their adjacent
identity JSON files and everything under `assets/` are evidence or listing
material, not extension-package uploads.

## Security boundary

Only the public Chrome item ID, public Edge CRX ID, and public or explicitly
future listing routes may be entered in `store-contract.json`. Partner Center
does not expose the actual Edge listing URL until publication; the final URL
must therefore be checked in the later publication gate. Keep account email
addresses, legal or identity documents, Seller IDs, Partner Center Product
IDs, API credentials, payment records, recovery codes, and screenshots
containing private account data outside the repository and outside chat.
