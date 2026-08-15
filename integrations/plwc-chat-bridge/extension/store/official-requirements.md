# Official Store Requirements Verified for STORE-G0-01

Verification date: 2026-08-15

Scope: requirements for establishing publisher ownership, creating unpublished
extension items, preparing listing and privacy disclosures, and retaining a
separate development identity. Store requirements in this record are derived
only from official Google Chrome and Microsoft documentation.

## Google Chrome Web Store

1. A publisher must register as a Chrome Web Store developer, accept the
   applicable agreement and policies, and pay the one-time registration fee.
   The official page does not state a durable fee amount; the Product Owner
   must verify the amount displayed during enrollment and must not record
   payment data in the repository.
2. The developer account requires a publisher name and verified contact email.
   Two-step verification must be enabled on the owning Google Account before
   publishing or updating an extension.
3. Website ownership can be verified through Google Search Console and then
   selected as the official URL in the listing. This is the appropriate public
   ownership proof for `plwc.de`; Search Console account data is not repository
   material.
4. A new item is created by uploading a valid ZIP. Uploading creates an item in
   the developer dashboard before submission. The dashboard item ID is the
   Chrome extension ID.
5. The Privacy practices tab requires a narrow single-purpose statement,
   justification for every declared permission, user-data disclosures,
   Limited Use certifications, and a privacy-policy URL consistent with actual
   behavior.
6. Extensions that handle user information must disclose the handling even if
   the data remains local. Website content, browsing activity, personal
   communications, and user-generated content are personal or sensitive user
   data categories under the policy.
7. Manifest V3 packages may not execute remotely hosted code. Requested access
   must be the narrowest access required by current functionality.
8. A listing needs an accurate detailed description, a 128 x 128 store icon,
   at least one screenshot at 1280 x 800 or 640 x 400 (maximum five), and a
   440 x 280 small promotional tile. A 1400 x 560 marquee image is optional.
9. Chrome supports deferred publishing after review, but review submission and
   any later publication are outside STORE-G0-01.
10. The manifest `key` controls a stable identity during development. The
    current PLwC key resolves only to the documented development/sideload ID.
    The new Chrome draft must be created from the keyless draft seed so its
    dashboard item ID is not silently assumed from the development identity.

### Official Chrome sources

- [Register your developer account](https://developer.chrome.com/docs/webstore/register)
- [Set up your developer account](https://developer.chrome.com/docs/webstore/set-up-account)
- [Use the Chrome Web Store API](https://developer.chrome.com/docs/webstore/using-api)
- [Publish in the Chrome Web Store](https://developer.chrome.com/docs/webstore/publish/)
- [Fill out the privacy fields](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy)
- [User Data FAQ](https://developer.chrome.com/docs/webstore/program-policies/user-data-faq)
- [Chrome Web Store Program Policies](https://developer.chrome.com/docs/webstore/program-policies/policies)
- [Additional requirements for Manifest V3](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements)
- [Complete your listing information](https://developer.chrome.com/docs/webstore/cws-dashboard-listing)
- [Creating a great listing page](https://developer.chrome.com/docs/webstore/best-listing)
- [Manifest `key`](https://developer.chrome.com/docs/extensions/reference/manifest/key)

## Microsoft Edge Add-ons

1. Publishing requires a Partner Center developer account enrolled in the
   Microsoft Edge program with a personal Microsoft account (MSA) as Primary
   Owner. A work or school account alone is not supported for enrollment.
2. The enrollment flow requires a permanent choice between Individual and
   Company, acceptance of the Microsoft Store App Developer Agreement, and
   completion of the displayed verification. Company accounts must verify
   their Microsoft Edge program information before publication.
3. Current official Edge enrollment documentation does not state a separate
   registration fee. The Product Owner must nevertheless confirm the live
   enrollment screen and keep any billing data out of the repository.
4. A new extension is created in Partner Center by uploading a valid ZIP.
   Product IDs shown inside Partner Center are account/workflow identifiers and
   must not be stored in this repository. Only the public Edge CRX ID and an
   ID-based future listing route belong in the Store contract before
   publication. The actual listing URL shown by Partner Center must be verified
   after publication is authorized in a later gate.
5. Visibility can be Public or Hidden. Hidden removes the extension from search
   but still uses a listing URL. Creating or saving a draft does not authorize
   certification or publication.
6. The current Privacy page requires a narrow Single Purpose, justification for
   every manifest permission, a remote-code answer, complete data-use
   declarations and certifications, and an accessible, current privacy policy.
7. Manifest V3 extensions must answer that they do not use remote code unless
   the package actually violates the MV3 restriction. PLwC bundles all
   extension JavaScript and does not fetch or evaluate executable code.
8. Microsoft requires only necessary permissions, disclosure of dependencies
   on separately installed software, a fully testable product, and complete
   certification notes.
9. For each listed language, Edge requires a 250-10,000 character description
   and a square logo (300 x 300 recommended; 128 x 128 minimum). It permits up
   to six optional screenshots at 1280 x 800 or 640 x 480. The 440 x 280 small
   and 1400 x 560 large promotional tiles are optional.
10. Microsoft explicitly states that a published Edge extension ID can differ
    from its sideload ID. A Native Messaging host serving both stores must list
    the exact IDs for both stores. That multi-identity change belongs to
    `BRIDGE-P0-03`.

### Official Microsoft sources

- [Register as a Microsoft Edge extension developer](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/create-dev-account)
- [Manage account settings](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/manage-settings)
- [Publish a Microsoft Edge extension](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension)
- [Developer policies for Microsoft Edge Add-ons](https://learn.microsoft.com/en-us/legal/microsoft-edge/extensions/developer-policies)
- [Native messaging](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/native-messaging)
- [Use the REST API to update an extension](https://learn.microsoft.com/en-us/microsoft-edge/extensions/update/api/using-addons-api)

## Local compliance result

- Manifest V3: compliant.
- Requested API permissions: limited to `storage` and `nativeMessaging`.
- Network host permission: limited to `ws://127.0.0.1:3007/*`.
- Content-script and exposed-resource matches: limited to `chatgpt.com` and the
  retained compatibility host `chat.openai.com`.
- Remotely hosted executable code: none found.
- External software dependency: must be prominent. The Store installs only the
  browser extension; PLwC Setup installs the Gateway, loopback Bridge, and
  Native Launcher.
- Privacy policy: required because the extension handles visible ChatGPT
  content, personal communications, tool inputs/results, conversation
  identifiers, and local settings.
- Public page deployment, publisher access, and both distinct unpublished
  Store identities: verified. Submission, certification, publication, and the
  final live Edge listing URL remain outside STORE-G0-01.
