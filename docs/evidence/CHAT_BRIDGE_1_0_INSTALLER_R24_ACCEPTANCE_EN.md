# PLwC Chat Bridge 1.0 — Installer r24 Acceptance Record

Date: 2026-08-29
Status: **HOLD — shortcut/update contracts, source validation, unsigned r24
artifact, pre-install update detection, installed update acceptance and the
public reviewer URL pass; live Store acceptance is pending**

This record is an addendum for `installer-r24`. The historical r22 and r23
acceptance records and their published artifacts remain unchanged.

## Release identity

| Field | Value |
| --- | --- |
| Product | PLwC Windows Setup |
| Product version | `1.0.0` |
| Windows installer revision | `installer-r24` |
| Gateway | `1.0.0` |
| Node Bridge | `1.0.0` |
| Browser Extension | `1.0.0` |
| Native Launcher | `1.0.0` |
| Signing disposition | Explicit unsigned build; Authenticode `NotSigned` |

## r24 change contract

`installer-r24` corrects the PLwC Configuration shortcuts without changing the
runtime or Store component versions:

1. The current-user desktop shortcut has the language-independent canonical
   name `PLwC-Konfiguration`.
2. Setup removes the three owned legacy variants `PLwC Konfiguration.lnk`,
   `PLwC configuration.lnk`, and `PLwC-Konfiguration.lnk` before recreating one
   canonical shortcut during install, update, or repair.
3. Configuration and Getting Started shortcuts explicitly use the installed
   `configuration/plwc.ico` asset instead of inheriting the Python executable
   icon.
4. Configuration launch uses a sibling `pythonw.exe` when available and safely
   falls back to the detected `python.exe` otherwise.
5. Unsigned r24 staging uses `.unsigned-build-r24`, preserving the historical
   local `.unsigned-build` r23 directory.
6. Update detection prefers the persisted `selection.ini` paths over duplicate
   per-value registry data, preventing a stale registry value from replacing a
   user-selected workspace.
7. The local configuration UI mirrors preserved profile, threshold and runtime
   choices back into `selection.ini`, updates the installed
   `plwc.example.json` Bridge configuration, accepts the legacy `plwc.json`
   filename, and can migrate Inno-generated UTF-16, UTF-8 and CP1252 client
   files.

The update continues to reuse the existing installation, runtime, workspace,
profile and configuration roots. It does not rename or recreate user data
directories.

## Verification record

| Gate | Result | Evidence |
| --- | --- | --- |
| Installer source, UI and payload contracts | `PASS` | Current r24 Pester rerun: 69 passed, 0 failed, 0 skipped under PowerShell 7; configuration integration tests: 13 passed under Python 3.12 |
| Canonical shortcut name and legacy cleanup | `PASS` | Contract assertions cover the fixed desktop name and all three owned legacy filenames |
| Explicit PLwC shortcut icon | `PASS` | Contract assertions require `IconFilename: "{app}\configuration\plwc.ico"` for configuration shortcuts |
| Windowless Python launcher preference | `PASS` | Contract assertion requires sibling `pythonw.exe` selection with `python.exe` fallback |
| Historical output preservation | `PASS` | r24 unsigned output root is distinct from the historical `.unsigned-build` directory |
| Explicit unsigned Setup candidate | `PASS` | `PLwC-Setup-1.0.0-installer-r24.exe`, 5,218,213 bytes, Authenticode `NotSigned`, SHA-256 `b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0` |
| Exact r24 build identity | `PASS` | Payload-manifest SHA-256 `81a8321aaba16f4e10da9c8dc2b2fd41142e361f19df4fa7e7b859d90f8e8e8d`; external-identity SHA-256 `a7560c5d12628383d61b854da251f3ecccc405504609e701bf8b527ae74a5d72`; every `SHA256SUMS.txt` entry verified |
| Existing-install preflight | `PASS` | German UI smoke against the installed r23 state logged `Existing PLwC installation detected=1; complete_settings=1`, displayed `installer-r24`, skipped the six repeated path/profile/runtime pages, reached the Update ready page, and stopped before installation |
| Installed r23-to-r24 shortcut acceptance | `PASS` | Explicit full update recorded final Setup SHA-256 `b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0` and `InstallAction=update`; exactly one `PLwC-Konfiguration.lnk` remains, targets Python 3.12 `pythonw.exe`, uses the installed `plwc.ico`, and carries workspace `F:\USER\PLWC_Arbeitsbereich`, profile `Sororitas`, thresholds `2/3/2`, Qdrant enabled and persona layer enabled. The preserved legacy `app\chat-bridge` installation root was reused rather than renamed. Live Bridge health returned build `plwc-chat-bridge@1.0.0` and eight public tools; the Native Launcher returned the same 1.0 component identity. |
| Public versioned reviewer URL | `PASS` | Public GitHub prerelease `plwc-setup-1.0.0-installer-r24`; anonymous HTTPS download reproduced 5,218,213 bytes and SHA-256 `b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0` exactly |
| Store-ID local readiness | `PASS` | The reproducible Store-package identity and secret scan passed. Chrome, Edge and Brave Native Messaging registrations resolve to the installed manifest, which allows the development, Chrome Store and Edge Store origins without a wildcard. Live health checks using each Store WebSocket origin returned build `plwc-chat-bridge@1.0.0` and exactly eight tools. |
| Live Store identity acceptance | `PENDING (external)` | The assigned Chrome URL returned `Element not available`; the assigned Edge URL returned `The requested page could not be found`. Both items remain unsubmitted drafts, so neither Store-signed extension can currently be installed. No review, certification or publication action was used. |

## Store-ID readiness probe - 2026-08-29

The local side of the serial Store gate is ready. The exact Chrome and Edge
origins both completed a live loopback health check against the installed r24
Bridge and returned the common 1.0.0 build identity with eight public tools.
The installed Native Launcher also reported both browser registrations and all
three approved extension origins correctly.

The external live acceptance cannot be executed while the items remain only
saved drafts. [Google documents](https://developer.chrome.com/docs/webstore/cws-dashboard-distribution)
that even private trusted-tester distribution uses the review flow, and
[Microsoft documents](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/submission-states)
that an `In draft` extension is not available to users. The concrete public
Store URLs confirmed that state on this date. Therefore this is a sequencing
block, not a product test failure:
an explicitly authorized review/certification step and an installable Store
channel are required before the real-ID Native Messaging, restart,
confirmation and missing-native-host matrix can run.

A read-only distribution check also found both drafts configured for public
visibility across all regions or markets. This has no effect while they remain
drafts, but it is not an appropriate controlled test channel. Before any review
submission, Chrome should be deliberately switched to a private trusted-tester
track and Edge to hidden link-only availability, or the Product Owner must
explicitly approve the current public distribution. No visibility setting was
changed during this probe.

## Release decision

The local r24 artifact, installed-update, public-reviewer-URL and Store-ID local
readiness gates are `PASS`; the external Store gates remain `HOLD`. Do not
relabel an older EXE as r24, do not overwrite historical evidence, and do not
submit or publish either Store draft without a separate explicit Product Owner
decision.
