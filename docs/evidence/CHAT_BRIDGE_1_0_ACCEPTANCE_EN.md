# PLwC Chat Bridge 1.0 Acceptance Record

Date: 2026-08-11  
Status: **HOLD — the explicit unsigned distribution and internal verification
pass; external Store publication and live browser acceptance are pending**

This record tracks the release boundary for PLwC Chat Bridge `1.0.0`. It does
not replace the historical `BRIDGE-P0-03` record and does not claim recovery of
the lost historical `installer-r21` executable.

## Release identity

| Item | Required identity |
| --- | --- |
| Chat Bridge release | `1.0.0` |
| Build ID | `plwc-chat-bridge@1.0.0` |
| Node Bridge | `1.0.0` |
| Browser Extension | `1.0.0` |
| Native Launcher | `1.0.0` |
| PLwC Gateway | `1.0.0` |
| PLwC Windows Setup product version | `1.0.0` |
| Windows installer revision | `installer-r22` |
| Installed Bridge directory | `chat-bridge-1.0.0` |

The retained development extension ID is
`nlogfcafjdfdoknpkbehjgihpafpipdb`. The Chrome Store ID is
`feceodobnhefdbfgmbinkndhogpfkicb`; the Edge Store ID is
`nncomjknhhlgcmkmlaljhkiojcnpmflb`. A version change must not alter these
identity assignments.

## Signing and explicit unsigned contract

The Product Owner decided on 2026-08-11 not to purchase a commercial personal
code-signing certificate. The accepted Windows candidate is therefore built
only through the explicit `-Unsigned` switch. The external build identity must
record `required: false`, `mode: explicit_unsigned`, and `NotSigned` for both
the Native Launcher and Setup EXE. Windows may identify its publisher as
unknown.

When signed mode is selected instead, an `installer-r22` build must:

1. use a valid Microsoft-signed x64 SignTool;
2. select one current-user certificate with the Code Signing EKU and an
   accessible private key;
3. sign the Native Messaging launcher with SHA-256 before the payload manifest
   is generated;
4. sign the outer Inno Setup executable with SHA-256;
5. timestamp both signatures through RFC 3161 with SHA-256;
6. verify both signatures and timestamps before writing the external build
   identity and `SHA256SUMS.txt`;
7. bind both verified signer records to the external build-identity JSON.

`build.ps1 -ValidateOnly` is explicitly non-distributable and performs no
signing. `build.ps1 -Unsigned` is the only permitted unsigned compile path; a
plain full build still fails closed without complete certificate settings. The
unsigned release output uses `installer/windows/.unsigned-build/`, and the
embedded Pester run uses `installer/windows/.test-build/`; neither may reset or
overwrite the real `installer/windows/stage/` or `installer/windows/dist/`
directories.

## Verification matrix

| Gate | Status | Required evidence |
| --- | --- | --- |
| Active 1.0 version and component contracts | `PASS` | PowerShell parse and JSON contract checks pass; release manifests, package metadata, installed paths, and current user guides resolve to `1.0.0`; historical records and mismatch fixtures remain unchanged |
| Node Bridge typecheck/build/tests | `PASS — 26/26` | `npm run check` under workspace version `1.0.0` |
| Extension typecheck/build/tests | `PASS — 173/173` | `npm run check` under extension version `1.0.0` |
| Cross-component Bridge and MCP registry contracts | `PASS — 9/9` | Targeted Python integration set |
| Full Python repository suite | `PASS — 55 passed, 6 skipped` | Complete `python -m pytest -q` run; no failure |
| Native Launcher compilation | `PASS` | Exact `plwc-chat-bridge@1.0.0` launcher source compiled successfully |
| Gateway MCPB 1.0 | `PASS` | `plwc-gateway-1.0.0.mcpb`, 67 allowlisted files, SHA-256 `5e870f40b9b3faea79d3997af9c657ef62c11295e85635a049214f7b63678fe7` |
| Microsoft SignTool installation | `PASS` | Windows SDK Build Tools `10.0.28000.0` x64 SignTool has a valid Microsoft Authenticode signature and successfully verifies an RFC 3161-timestamped signed file |
| Store package reproducibility and secret scan | `PASS` | Two reproducible 1.0 Store ZIPs, four-entry allowlist, identity sidecars and secret scan pass |
| Installer contracts in isolated test output | `PASS — 67/67` | Real stage/dist trees remained byte- and metadata-identical across the embedded ValidateOnly build |
| Accidental unsigned production-build rejection | `PASS` | Missing certificate configuration without `-Unsigned` fails before stage/dist reset |
| Explicit unsigned Native Launcher | `PASS` | Authenticode status `NotSigned`; external build identity records `required: false` and `mode: explicit_unsigned` |
| Explicit unsigned Setup EXE | `PASS` | Authenticode status `NotSigned`; SHA-256 `b4f34b6a42a19f060e0765c1be9ef82e39ea813cf46e97576e3fb5357576ab5a` |
| Exact unsigned `installer-r22` identity | `PASS` | Payload-manifest SHA-256 `957ed84920949ce91e550f87471dd06901da1040aa5ae5eb0a62f4efed551666`; external-identity SHA-256 `92ea1290e54aa39468ca56f29f7742bac6cfb7fed2e856e3fab32b6206568399`; exact `SHA256SUMS.txt` verified |
| Chrome Store identity in Chrome and Brave | `PENDING (external)` | Live acceptance under the assigned Chrome Store ID |
| Edge Store identity in Edge | `PENDING (external)` | Live acceptance under the assigned Edge Store ID |
| Final Store screenshots and public versioned Setup URL | `PENDING (external)` | Sanitized final captures and published exact artifact route |
| Renewed H2 | `HOLD` | Bind the exact unsigned and live-accepted release set after Store publication |

## Internal artifact evidence

The reproducible Chrome/Brave and Edge Store archives contain exactly
`background.js`, `content.js`, `icons/plwc-icon-512.png`, and `manifest.json`.
Both archives are `276737` bytes and have SHA-256
`62d4b78f0787b0ce22134e4426dfdea90282e0d3245afbf48f0c6f11b4427936`.
The adjacent sidecars bind those same bytes separately to the assigned Chrome
and Edge Store identities. Store-side signing will bind the keyless extension
content to the two public items.

The Chrome/Brave sidecar has SHA-256
`1876a4e0c1daf87db60bd04ab9ee6e4e0d33441e3feec12fc57e5d55ffd46e7f`;
the Edge sidecar has SHA-256
`bec9f841fc02343281bb6a1d04a0ee7faf6a8dee2f3ef176c5b1e053703dda83`.

The exact explicit unsigned Windows release candidate is
`PLwC-Setup-1.0.0-installer-r22.exe`, SHA-256
`b4f34b6a42a19f060e0765c1be9ef82e39ea813cf46e97576e3fb5357576ab5a`.
Its payload manifest has SHA-256
`957ed84920949ce91e550f87471dd06901da1040aa5ae5eb0a62f4efed551666`,
and its external build identity has SHA-256
`92ea1290e54aa39468ca56f29f7742bac6cfb7fed2e856e3fab32b6206568399`.
The external identity records Gateway, Node Bridge, Browser Extension, and
Native Launcher as `1.0.0`, plus `NotSigned` for both Windows executables.

For the embedded Pester run, the canonical real-tree snapshots before and after
the suite were identical:

| Tree | Snapshot SHA-256 |
| --- | --- |
| `installer/windows/stage` | `b8d8bcef30069024f8c6bf71d8dad3201288c98ce38598842896d0d933ac9327` |
| `installer/windows/dist` | `55c0296296492b97b3582fef8f56e5a0ba4d5c38c5a957af0cfbd14846620f2d` |

These are hashes of canonical path/type/length/time/file-hash snapshot data,
not substitutes for the exact explicit unsigned release-artifact hashes above.

## Historical artifact preservation

An earlier embedded `build.ps1 -ValidateOnly` Pester invocation reset the real
`installer/windows/stage` and `installer/windows/dist` directories. The handed
over historical `installer-r21` executable, its external identity, and its
then-current distribution evidence were removed or overwritten. No byte-equal
copy with the historical hash was found. Repository history was not rewritten,
and the current contents of `dist` are not accepted as a replacement.

The isolated test-output change prevents a repeat of that failure mode. It does
not reconstruct or relabel the lost artifact.

## Release decision

Formal Chat Bridge 1.0 release gate: `HOLD`.

The gate may move to `PASS` only for the exact explicitly unsigned
`installer-r22` artifact whose hashes, unsigned-status evidence, Store packages,
live browser acceptance, screenshots, public download route, and renewed H2 are
all bound in this record.
