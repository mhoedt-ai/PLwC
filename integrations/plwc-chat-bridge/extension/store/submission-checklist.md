# PLwC Chat Bridge Store Submission Checklist

Status: `DRAFTS SAVED / HOLD`

This record binds the completed draft-only dashboard session. It is not
authorization to submit for review, certify, or publish either extension.

## Bound identities and packages

| Target | Existing draft ID | Upload candidate | SHA-256 |
| --- | --- | --- | --- |
| Chrome / Brave | `feceodobnhefdbfgmbinkndhogpfkicb` | `store/out/PLwC-Chat-Bridge-1.0.0-chrome-brave-store.zip` | `62d4b78f0787b0ce22134e4426dfdea90282e0d3245afbf48f0c6f11b4427936` |
| Microsoft Edge | `nncomjknhhlgcmkmlaljhkiojcnpmflb` | `store/out/PLwC-Chat-Bridge-1.0.0-edge-store.zip` | `62d4b78f0787b0ce22134e4426dfdea90282e0d3245afbf48f0c6f11b4427936` |

The identical ZIP bytes are intentional. Each store signs the keyless runtime
for its own public identity. Upload only the ZIP for the matching existing
draft. Do not create another item, and do not upload the adjacent
`*-store-build-identity.json` evidence file.

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

## Preflight before any dashboard change

- Re-run `npm run test:store:windows` from the extension directory.
- Confirm both ZIP hashes against the table above and their identity sidecars.
- Confirm manifest version and version name are both `1.0.0`.
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

## HOLD conditions before review submission

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

## HOLD conditions before public publication

- Obtain an installable, review-approved Store channel under a separate,
  explicit Product Owner decision. A saved Chrome or Edge draft alone is not
  installable: Chrome trusted-tester/private distribution still uses Store
  review, and Microsoft documents `In draft` as unavailable to users.
- Install the review-approved packages under their real Chrome and Edge Store
  identities and complete live Native Messaging, loopback, tool-contract,
  confirmation, restart, and missing-native-host acceptance.
- Verify the three prepared 1280 x 800 screenshots against that accepted
  Store-ID build using synthetic data; replace any image that no longer matches
  the live 1.0 UI.
- Renew the H2 handoff and bind the Setup hash, public URL, Gateway identity,
  Bridge identity, and both Store package identities.

Review submission and public publication remain separate Product Owner
decisions. Chrome's deferred-publishing option may be selected at submission,
but a reviewed submission must not be treated as authorization to publish.
