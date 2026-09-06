# PLwC Chat Bridge 1.0 — Installer r23 Acceptance Record

Date: 2026-08-15
Status: **HOLD — internal update, configuration, unsigned-build, public-artifact
and Chrome reviewer-record checks pass; the Edge reviewer record and live Store
acceptance are pending**

This record is an addendum for `installer-r23`. The historical
`CHAT_BRIDGE_1_0_ACCEPTANCE_EN.md` record remains the immutable evidence for
`installer-r22`; r23 does not replace, relabel or alter that artifact.

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
| Windows installer revision | `installer-r23` |
| Fresh-install Gateway directory | `gateway` |
| Fresh-install Bridge directory | `bridge` |

## r23 change boundary

`installer-r23` adds three non-destructive installation contracts:

1. Fresh installations use stable `app\gateway` and `app\bridge` runtime
   directories without a version suffix.
2. A complete existing PLwC installation is detected as an update. Stored
   directories and runtime choices are reused, and the six directory/profile/
   runtime pages are skipped instead of being requested again.
3. The installed bilingual configuration page can change the shared workspace
   later. Saving synchronizes Gateway, Chat Bridge, Codex, Odysseus, installer
   selection and the current-user installer state. Only missing `Tagebuch`,
   `Temp` and `Trashcan` directories are created; existing content is not
   moved, overwritten or deleted.

An update preserves an older versioned Gateway or Bridge path that is already
in use. Stable names are fresh-install defaults, not authority to migrate or
delete existing user directories.

## Signing contract

The Product Owner requires this Windows candidate to remain unsigned. It is
built only with the explicit `-Unsigned` switch. The external build identity
must record `required: false`, `mode: explicit_unsigned`, and `NotSigned` for
both the Native Launcher and Setup EXE. No Store submission or publication is
authorized by this record.

## Verification matrix

| Gate | Status | Evidence |
| --- | --- | --- |
| Stable runtime-directory contracts | `PASS` | Source and Pester contracts require fresh `gateway` and `bridge` directories; versioned package artifact names remain intentional |
| Existing-install update detection | `PASS` | Real UI smoke with the exact final r23 EXE (SHA-256 `08e21dc0d92aa125f340a99ed0fc00e4e6c05cef764e60a2f6a0a37050523a10`) against the installed r22 state logged `detected=1; complete_settings=1` and reached Ready without the six directory/profile/runtime pages; installation was not started |
| Non-destructive legacy-path handling | `PASS` | Installer source reuses stored paths and does not move or delete legacy runtime directories |
| Workspace editing and cross-client synchronization | `PASS` | Configuration service/UI integration tests cover path validation, directory creation, installer state and generated Gateway/Bridge/Codex/Odysseus configuration |
| Existing runtime-choice preservation | `PASS` | Integration test confirms profile, thresholds, Qdrant and Persona settings survive installer-owned workspace synchronization |
| Full Python repository suite | `PASS — 58 passed, 6 skipped` | Complete `python -m pytest -q` run |
| Node Bridge tests | `PASS — 26/26` | Workspace check completed for Bridge `1.0.0` |
| Browser Extension tests | `PASS — 173/173` | Workspace check completed for Extension `1.0.0` |
| Full Windows installer Pester suite | `PASS — 69/69` | Completed through the mapped workspace path in isolated `.test-build` output without changing canonical `stage` or `dist`; a preceding UNC invocation failed at a .NET path-format boundary before staging and is not an installer failure |
| Explicit unsigned Setup candidate | `PASS` | `PLwC-Setup-1.0.0-installer-r23.exe`, 5,218,577 bytes, Authenticode `NotSigned`, SHA-256 `08e21dc0d92aa125f340a99ed0fc00e4e6c05cef764e60a2f6a0a37050523a10` |
| Exact r23 build identity | `PASS` | Payload-manifest SHA-256 `73ac6bbc041803f4e15cda6182c5f62aac1550d931f19a299d43afec90e8e3ce`; external-identity SHA-256 `c29d4f8aa4b76ae52aa56b731be8b319b78700ef6e52a14ecd742d0243059404`; every `SHA256SUMS.txt` entry verified |
| Public versioned r23 reviewer URL | `PASS` | Anonymous HTTPS download from the new r23 prerelease returned 5,218,577 bytes, SHA-256 `08e21dc0d92aa125f340a99ed0fc00e4e6c05cef764e60a2f6a0a37050523a10`, byte equality with the local candidate and Authenticode `NotSigned`; GitHub reports the same asset digest |
| Chrome saved reviewer record | `PASS` | The draft test instructions contain the public r23 URL and exact SHA-256; the former r22 reference is absent; the item remains an unsubmitted draft |
| Edge reviewer/certification record | `PENDING (external)` | Partner Center exposes no editable certification-note field outside the Publish flow; the draft remains unchanged and unsubmitted because entering that flow requires explicit Product Owner authorization |
| Live Store identity acceptance | `PENDING (external)` | Chrome/Brave and Edge tests under the assigned Store identities |

## Historical preservation and release decision

The exact local reviewer candidate is:

```text
PLwC-Setup-1.0.0-installer-r23.exe
SHA-256 08e21dc0d92aa125f340a99ed0fc00e4e6c05cef764e60a2f6a0a37050523a10
Build ID plwc-windows-setup@1.0.0/installer-r23#sha256:08e21dc0d92aa125f340a99ed0fc00e4e6c05cef764e60a2f6a0a37050523a10
```

The public reviewer URL is:

```text
https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r23/PLwC-Setup-1.0.0-installer-r23.exe
```

The external identity records `explicit_unsigned`, `NotSigned` for both Setup
and the Native Launcher, and `1.0.0` for Gateway, Node Bridge, Browser
Extension and Native Launcher.

The public `installer-r22` prerelease and its acceptance record remain
unchanged. The previously lost historical `installer-r21` executable is not
reconstructed or relabelled.

Formal r23 reviewer-artifact gate: `PASS`.

The overall Chat Bridge 1.0 Store gate remains `HOLD` until the Edge reviewer
record can be supplied in an explicitly authorized submission flow and live
Store-identity acceptance is complete. Store submission remains a separate
explicit Product Owner decision.
