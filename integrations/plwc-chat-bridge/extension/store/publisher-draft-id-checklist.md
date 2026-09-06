# Publisher and Draft Identity Checklist

Owner: Product Owner

Repository rule: complete only the checkboxes below and the public fields in
`store-contract.json`. Never paste account emails, legal names/addresses,
identity documents, Seller IDs, Partner Center Product IDs, client IDs, API
keys, access/refresh tokens, payment details, receipts, recovery codes, or
account screenshots into the repository or chat.

## Preconditions

- [x] Confirm that the intended public publisher/support identity and
  `info@plwc.de` are approved for public use.
- [x] Verify control of `plwc.de` through the relevant publisher workflow; keep
  Search Console and DNS evidence outside the repository.
- [x] Deploy `public/chat-bridge/privacy/index.html`,
  `public/chat-bridge/support/index.html`, and
  `public/chat-bridge/store-pages.css` to the existing website paths.
- [x] Confirm both target URLs return the intended page over HTTPS without
  authentication, redirect loops, certificate warnings, or `noindex`.
- [x] Set both public-page statuses in `store-contract.json` to `verified` only
  after the live checks pass.

## Chrome Web Store publisher

- [x] Register the dedicated Chrome Web Store developer account, accept the
  current agreement/policies, and complete the fee shown by Google.
- [x] Verify the contact email and enable two-step verification on the owning
  Google Account.
- [x] Set the approved publisher name and verify `https://plwc.de/` through the
  official URL workflow. Select it in the final item listing during
  `STORE-P0-02` if the draft form requires unrelated submission fields.
- [x] Confirm dashboard access and item-management authority. Record no account
  identifiers or enrollment evidence in the repository.

## Chrome unpublished item

- [x] Build the keyless `DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT` ZIP with the
  provided script and verify the current development `key` is absent.
- [x] Choose Add new item and upload the seed once.
- [x] Save the item as an unpublished draft. Do not select Submit for Review.
- [x] Copy only the 32-letter public item/extension ID into
  `stores.chrome.extensionId` in `store-contract.json`.
- [x] Copy only its canonical public listing URL into
  `stores.chrome.listingUrl` in `store-contract.json`.
- [x] Confirm the Chrome ID differs from the retained development ID
  `nlogfcafjdfdoknpkbehjgihpafpipdb`.

## Microsoft Edge Add-ons publisher

- [x] Enroll in the Microsoft Edge program with a personal Microsoft account
  as Primary Owner and choose the correct permanent account type.
- [x] Accept the current agreement and complete every verification shown by
  Partner Center; for a Company account, confirm company verification is
  complete.
- [x] Confirm Edge dashboard access and extension-management authority. Record
  no Seller ID, Product ID, tenant ID, account identity, or verification
  evidence in the repository.

## Edge unpublished item

- [x] Create a new extension in Partner Center and upload the same keyless
  `DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT` ZIP once.
- [x] Save the extension as a draft. Do not publish or start certification.
- [x] Copy only the public 32-letter Edge CRX/extension ID into
  `stores.edge.extensionId` in `store-contract.json`.
- [x] Record the public ID-based Microsoft Edge Add-ons listing route in
  `stores.edge.listingUrl`. Partner Center reports that the actual listing URL
  is unavailable until publication; verify the final canonical URL during
  `STORE-P0-02` without publishing during this gate.
- [x] Confirm the Edge ID differs from the retained development ID and from the
  Chrome Store ID.

## Gate review

- [x] Run `npm run check` in the extension directory.
- [x] Run the STORE-G0-01 static contract test and the external HTTPS checks.
- [x] Verify `git diff` and `git status` contain no generated seed ZIP, private
  account artifact, credentials, payment material, or recovery material.
- [x] Update `docs/evidence/STORE_G0_01_ACCEPTANCE_EN.md` with public facts only.
- [x] Mark STORE-G0-01 `PASS` only when both publisher ownership checks, both
  live page checks, and both distinct public Store IDs are actually verified.
- [x] Keep submission, certification, and publication pending for
  `STORE-P0-02`; keep final identity-aware packaging pending for
  `BRIDGE-P0-03`.
