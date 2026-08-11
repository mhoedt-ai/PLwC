# BRIDGE-P0-03 Acceptance Record

Date: 2026-08-10

Status: **HOLD — internal package and multi-identity contracts pass; real
Store-identity browser acceptance and renewed H2 are pending**

No Store upload, review submission, certification, publication, account action,
agreement acceptance, or browser-consent bypass was performed.

## Scope and outcome

The internal work for `BRIDGE-P0-03: Store Package and Multi-Identity Contract`
is implemented and automated. The current common component identity remains:

```text
Build ID:        plwc-chat-bridge@0.2.0-rc19.dev20
Node Bridge:     0.2.0-rc19.dev20
Extension:       0.2.0-rc19.dev20
Native Launcher: 0.2.0-rc19.dev20
```

The gate is not marked PASS. The two real Store identities have not yet been
installed and exercised in Chrome, Brave, and Edge with the exact candidate
packages and native launcher. The five final Store screenshots, an exact
versioned public Setup artifact URL, and the renewed H2 handoff are also absent.

## Canonical identity contract

`integrations/plwc-chat-bridge/native/extension-identity.json` is the canonical
runtime identity contract. Compatibility aliases retain the development ID for
the pre-Store Installer track, while the versioned contract names all three
identities explicitly:

| Identity | Classification | Native Messaging origin |
| --- | --- | --- |
| `nlogfcafjdfdoknpkbehjgihpafpipdb` | Development/sideload only | `chrome-extension://nlogfcafjdfdoknpkbehjgihpafpipdb/` |
| `feceodobnhefdbfgmbinkndhogpfkicb` | Chrome Web Store / Chrome package used by Brave | `chrome-extension://feceodobnhefdbfgmbinkndhogpfkicb/` |
| `nncomjknhhlgcmkmlaljhkiojcnpmflb` | Microsoft Edge Add-ons | `chrome-extension://nncomjknhhlgcmkmlaljhkiojcnpmflb/` |

The Native Messaging manifest and generated launcher manifest contain exactly
those origins. The registration command rejects any requested extension ID not
in the contract. The loopback Bridge accepts exactly the corresponding
WebSocket Origin header values without a trailing slash. There is no wildcard.

The Native Launcher performs the full build-identity and `8/8` tool health check
through all three approved WebSocket origins before reporting ready.

## Store package result

Commands:

```powershell
npm run test:store:windows
npm run build:store:windows
```

Both final-candidate ZIPs contain exactly these entries:

```text
background.js
content.js
icons/plwc-icon-512.png
manifest.json
```

`manifest.json` is at the archive root. Its development `key` is absent. Source
maps, source files, package metadata, Store contracts, repository documentation,
key-file formats, environment files, and private material are absent. The
builder scans JavaScript and JSON for high-confidence private-key, API-key,
token, password, AWS, GitHub-token, and OpenAI-key patterns.

| Target | Expected Store ID | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Chrome/Brave | `feceodobnhefdbfgmbinkndhogpfkicb` | 276,774 | `667d6c4de46c5c961f7161baa9c20a800c5b653d900aac516d68ee792e2323f2` |
| Edge | `nncomjknhhlgcmkmlaljhkiojcnpmflb` | 276,774 | `667d6c4de46c5c961f7161baa9c20a800c5b653d900aac516d68ee792e2323f2` |

The ZIP bytes are intentionally identical because both stores sign the same
keyless runtime content under different item identities. Separate adjacent
build-identity sidecars bind the filename and SHA-256 to the expected Store ID
and Native Messaging origin. Sidecars are evidence and are not ZIP entries.

The reproducibility test built both targets twice in separate directories and
confirmed byte-identical ZIPs and sidecars.

## Missing Native Launcher boundary

When Chrome reports the native host as missing, the extension Status view:

- says that the browser Store installs only the extension;
- says that PLwC Setup installs the local application and Native Launcher;
- links to the official PLwC releases page;
- never claims that Add/Get installs or repairs native software.

The official releases page currently exposes the earlier Gateway prerelease,
not a versioned Setup artifact for this Store build. Therefore the generic
releases URL is a safe user route but does not close the reviewer-artifact
requirement. `store-contract.json` records
`pending_versioned_setup_publication`, and `listing-en.md` still requires the
exact tested Setup URL before submission.

## Store material result

The following English materials are complete and source-aligned:

- single purpose and detailed listing description;
- every manifest permission and host justification;
- remote-code answer;
- conservative data-use categories and Limited Use declarations;
- retention, deletion, local-processing, OpenAI-processing, and support rules;
- external-software dependency disclosure;
- reviewer steps and expected network boundary;
- five-shot 1280 x 800 screenshot specification and promotional-asset sizes.

Actual final screenshots are pending. Development-ID or fixture screenshots are
not accepted as substitutes for captures from the real Store-ID build.

## Automated verification

| Check | Result |
| --- | --- |
| Node Bridge typecheck/build/tests | `PASS — 26/26` |
| Extension typecheck/build/tests | `PASS — 173/173` |
| All eight public tools with 50–100 KB Unicode chunk transport | `PASS` |
| Windows Native Launcher compilation | `PASS` |
| Store package reproducibility/inventory/identity/secret scan | `PASS` |
| Python cross-component Bridge and MCP registry contracts | `PASS — 9/9` |
| Existing Installer source and payload contracts | `PASS — 66/66` |

The complete command `npm run check:windows` passed. The existing Installer
Pester suite also passed all `66/66` source, prerequisite, UI, stage, payload,
hash-manifest, privacy, and output-boundary contracts. Its embedded
`build.ps1 -ValidateOnly` run is diagnostic evidence only and does not replace
`SETUP-P0-05`.

## External completion matrix

| Requirement | Current status | Evidence required for PASS |
| --- | --- | --- |
| Chrome Store identity in Chrome | `PENDING (external)` | Install the exact Chrome candidate under ID `fece...kicb`; verify panel, build identity, `8/8`, read-only call, confirmation boundary, complete result, launcher restart, and missing-host route. |
| Chrome Store identity in Brave | `PENDING (external)` | Repeat the exact Chrome-package and Native Messaging path in current Brave. |
| Edge Store identity in Edge | `PENDING (external)` | Install the exact Edge candidate under ID `nnco...mflb` and repeat the same acceptance. |
| Final Store screenshots | `PENDING (external)` | Capture the specified five sanitized 1280 x 800 PNGs from the final Store-ID build. |
| Exact public Setup reviewer artifact | `PENDING (external)` | Publish or otherwise provide the Product-Owner-approved versioned Setup artifact and record its URL and SHA-256 without submitting the extension. |
| Renewed H2 | `HOLD` | Hash the exact accepted Bridge, extension, launcher, identity contract, and Store ZIPs after the live tests; then issue H2. |

`SETUP-P0-05` must not start while this matrix remains open.

## Preservation note for the inherited r21 artifact

The existing Installer Pester suite contains an embedded `build.ps1
-ValidateOnly` invocation. During this run it reset the generated
`installer/windows/stage` and `installer/windows/dist` directories before the
outer command timed out. The inherited r21 EXE with historical SHA-256
`5c4637ae2f967fc406102f09ed6c19266b836a08fd1043817556addc914a76e7` is no
longer present in the local `dist` directory, and a search of the project drive,
user downloads, desktop, temporary files, and Codex attachments found no
byte-identical copy. The historical acceptance record and hash were not
rewritten. No replacement EXE is claimed, and no Store-specific Setup candidate
was built.

## Disposition

Internal BRIDGE-P0-03 implementation: `PASS`.

Formal BRIDGE-P0-03 gate: `HOLD`.

H2: not reissued.

Submission, certification, publication, and `SETUP-P0-05`: not authorized by
this record.
