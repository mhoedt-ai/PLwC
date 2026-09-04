# PLwC Chat Bridge Store Submission Checklist

Status: `CHROME 1.0.1 PRIVATE DRAFT / EDGE 1.0.1 HIDDEN UPDATE DRAFT / PUBLICATION HOLD`

This record binds the completed draft preparation and controlled review
submission. It is not authorization for a later Chrome publication, a change
to public visibility, or any broader distribution of either extension.

## Current dashboard recheck and Edge update - 2026-09-04

- Chrome item `feceodobnhefdbfgmbinkndhogpfkicb`, version `1.0.0`, was accepted
  and showed `Bereit zur Veröffentlichung`. Google displayed 2026-10-01 as the
  latest publication date.
- Active Chrome visibility was still **Private**, with no selected trusted-tester
  group. The accepted item is therefore not a usable link distribution.
- Chrome disabled package upload while the accepted deferred-publication draft
  is pending. Its menu offers `Cancel publication`; using that action would
  discard the accepted publication state before a `1.0.1` update can be
  uploaded. The Product Owner used that action, returning the item to an
  editable draft without publishing `1.0.0`.
- The verified `PLwC-Chat-Bridge-1.0.1-chrome-brave-store.zip` package was then
  uploaded to the same Chrome item and saved. Chrome shows version `1.0.1`,
  status **Draft**, visibility **Private**, no trusted-tester group, and no
  published version. `Submit for review` was not used.
- The intended Chrome distribution is **Unlisted**, reachable only through the
  official Store link. Before any publication action, recheck active visibility;
  if changing it triggers another review, wait for that review to finish.
- Edge was reverified as version `1.0.0`, status **Live**, visibility **Hidden**,
  with CRX ID `nncomjknhhlgcmkmlaljhkiojcnpmflb` and the expected direct Store
  link. This is the intended link-only distribution model.
- After Product Owner authorization to renew the extensions, the verified
  `PLwC-Chat-Bridge-1.0.1-edge-store.zip` package was uploaded to the existing
  Edge identity. Partner Center verified version `1.0.1`; the resulting update
  is **In draft** and remains **Hidden** while live version `1.0.0` continues to
  be available. The `Publish` action was not used.
- No Store publication, review submission, or Chrome visibility change is
  authorized by this checklist.

## Previously review-bound identities and packages

| Target | Existing draft ID | Review-bound package | SHA-256 |
| --- | --- | --- | --- |
| Chrome / Brave | `feceodobnhefdbfgmbinkndhogpfkicb` | `store/out/PLwC-Chat-Bridge-1.0.0-chrome-brave-store.zip` | `62d4b78f0787b0ce22134e4426dfdea90282e0d3245afbf48f0c6f11b4427936` |
| Microsoft Edge | `nncomjknhhlgcmkmlaljhkiojcnpmflb` | `store/out/PLwC-Chat-Bridge-1.0.0-edge-store.zip` | `62d4b78f0787b0ce22134e4426dfdea90282e0d3245afbf48f0c6f11b4427936` |

The identical ZIP bytes are intentional. Each store signs the keyless runtime
for its own public identity. Upload only the ZIP for the matching existing
draft. Do not create another item, and do not upload the adjacent
`*-store-build-identity.json` evidence file.

## Prepared r26 extension update

The current r26 source produces extension package version `1.0.1` while the
shared PLwC/Bridge protocol release remains `1.0.0`. The Store builder records
both versions separately and has passed its reproducibility, four-entry
allowlist, identity, development-key-removal, source-map-exclusion, and secret
scan tests.

| Target | Existing item ID | Prepared package | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| Chrome / Brave | `feceodobnhefdbfgmbinkndhogpfkicb` | `store/out/PLwC-Chat-Bridge-1.0.1-chrome-brave-store.zip` | 281.201 | `6412dcc2ea32f2d99fc34a7402423326e99ee683c5a192014be4fb93f621ce7f` |
| Microsoft Edge | `nncomjknhhlgcmkmlaljhkiojcnpmflb` | `store/out/PLwC-Chat-Bridge-1.0.1-edge-store.zip` | 281.201 | `6412dcc2ea32f2d99fc34a7402423326e99ee683c5a192014be4fb93f621ce7f` |

Both rows are now bound to the verified drafts recorded above: Chrome `1.0.1`
is a private draft and Edge `1.0.1` is a hidden update draft. Neither row is
proof of a new review or publication. Before any further upload, re-read the
live item ID, version, review state, and visibility. Upload only to the matching
existing item and never create a replacement item.

## Saved draft result - 2026-08-15

- Chrome accepted the bound Chrome / Brave ZIP as version `1.0.0` in the
  existing item `feceodobnhefdbfgmbinkndhogpfkicb`. The English listing,
  static graphics, privacy declarations, permission justifications, and public
  privacy and support URLs were saved. No review submission or publication was
  requested.
- Edge accepted the bound Edge ZIP as version `1.0.0` in the existing public
  CRX identity `nncomjknhhlgcmkmlaljhkiojcnpmflb`. Package, availability,
  properties, privacy, and the English Store listing were saved as completed
  draft steps. The extension overview was re-read and showed `Version 1.0.0`
  and `In draft`. The public support contact URL was separately saved and
  visually re-read after navigation. The enabled `Publish` action was not used.
- The Chrome package and Edge package displayed only `storage`,
  `nativeMessaging`, and the loopback origin `ws://127.0.0.1:3007/*` as their
  requested permissions or host access.
- The exact explicitly unsigned Setup reviewer artifact is publicly available
  at the versioned URL recorded in `store-contract.json`. An anonymous HTTPS
  download reproduced SHA-256
  `b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0`
  and Authenticode status `NotSigned`. Chrome saved the matching 445-character
  reviewer test instruction without credentials.
- On 2026-08-29, the three privacy-sanitized 1280 x 800 Store-candidate
  screenshots were uploaded to and saved in both existing Store drafts. Chrome
  continued to show `Status: Entwurf`; Edge contained the same three named
  files and confirmed the saved draft. Neither `Prüfen lassen` nor `Publish`
  was used.
- No developer-account, Partner Center, payment, recovery, or other private
  identifiers are part of this record.

## Controlled review submission - 2026-08-30

- After explicit Product Owner confirmation, Chrome was submitted as private
  for the configured trusted tester. The dashboard reported
  `Überprüfung ausstehend`. Automatic publication after approval was disabled.
  Chrome states that a deferred-publication item expires 30 days after it
  passes review; plan the controlled availability decision inside that window.
- After a second action-time confirmation of the exact public certification
  text, Edge was submitted as hidden/link-only. Partner Center reported
  `In review` and an expected response within seven business days.
- The Edge certification note contained the exact public unsigned r24 Setup
  URL and SHA-256, synthetic test steps, local dependency information and the
  loopback/publisher-network boundary. It contained no credential or private
  account data.
- Neither submitted package is currently an installable Store-signed channel.
  Review approval and real-ID live acceptance remain open gates.

## Preflight before any dashboard change

- Re-run `npm run test:store:windows` from the extension directory.
- Confirm both ZIP hashes against the table above and their identity sidecars.
- Confirm manifest version and version name are both `1.0.1`; confirm the
  adjacent identity sidecar separately binds shared release `1.0.0` and build
  `plwc-chat-bridge@1.0.0`.
- Confirm the existing dashboard item ID matches the target row before upload.
- Keep the privacy and support pages publicly reachable over HTTPS.
- Keep publisher account, legal, payment, recovery, and Partner Center data out
  of the repository, screenshots, and chat.

## Executed dashboard order

1. Open the existing unpublished Chrome item and verify its item ID.
2. Upload only the Chrome / Brave ZIP as a package update.
3. Fill the English listing, privacy declarations, permission justifications,
   remote-code answer, support links, and reviewer notes from `listing-en.md`.
4. Add the 128 x 128 icon and 440 x 280 small promotional tile from `assets/`.
5. Save the Chrome draft without submitting it for review.
6. Open the existing unpublished Edge item and verify its public CRX ID.
7. Upload only the Edge ZIP as a package update.
8. Fill the Edge properties, privacy declarations, certification notes, and
   dependencies from `listing-en.md`.
9. Add the 300 x 300 Edge logo and save the Edge draft without submission.
10. Re-read both saved drafts and confirm neither Store identity changed.

Chrome is first only to make the package/listing review easy to repeat in Edge;
the order has no release or priority meaning.

## Completed gates before review submission

- Completed on 2026-08-15: publish the exact versioned, explicitly unsigned
  PLwC Windows Setup candidate and bind its stable public HTTPS URL in
  `store-contract.json`.
- Completed on 2026-08-29: re-run the reproducible Store-package identity and
  secret scan; verify the installed Chrome, Edge and Brave Native Messaging
  registrations; and pass live Bridge health checks with both assigned Store
  origins, common build `plwc-chat-bridge@1.0.0` and exactly eight tools.
- Completed on 2026-08-29 after an explicit Product Owner decision: save Chrome
  as private and Edge as hidden/link-only. Both settings persisted and both
  items remained drafts. No review or publication action was used.
- Completed on 2026-08-29 after a separate explicit Product Owner decision:
  save one approved individual Chrome trusted tester at publisher-account
  level and verify persistence after reload. Keep the tester address out of the
  repository; do not treat tester configuration as authorization to submit.
- Completed on 2026-08-29: publish the comprehensive PLwC 1.0 software
  description and align the installation, configuration, security,
  troubleshooting, tester and component documentation with the exact unsigned
  r24 candidate, stable fresh-install runtime paths, update behavior and saved
  Store-draft state. Historical rc and installer evidence remains unchanged.

## HOLD conditions before Store availability or publication

- Recheck both live dashboards. Chrome is review-accepted but remains Private
  without a selected tester group and is not link-installable. The current Edge
  state is not established by this dated repository record.
- Change Chrome to the authorized Unlisted/link-only model only after explicit
  approval. If the change triggers a new review, wait for that review to finish.
- Complete the controlled availability decision and real-ID acceptance before
  the dashboard's 2026-10-01 Chrome deadline.
- Install the review-approved packages under their real Chrome and Edge Store
  identities and complete live Native Messaging, loopback, tool-contract,
  confirmation, restart, and missing-native-host acceptance.
- Verify the three prepared 1280 x 800 screenshots against that accepted
  Store-ID build using synthetic data; replace any image that no longer matches
  the live 1.0 UI.
- Renew the H2 handoff and bind the Setup hash, public URL, Gateway identity,
  Bridge identity, and both Store package identities.

Review approval, controlled private/hidden availability and any later public
publication remain separate gates. Chrome's deferred-publishing option is
active, and a reviewed submission must not be treated as authorization to
publish.
