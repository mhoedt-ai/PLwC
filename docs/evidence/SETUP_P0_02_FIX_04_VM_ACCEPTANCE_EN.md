# PLwC Windows Setup r14 Preserved-VM Acceptance Record

Acceptance date: 2026-08-08  
Evidence package: `SETUP-P0-02-FIX-04`  
Fix: `PLWC-P1-02-FIX-01`  
Result: **PASS**

## 1. Acceptance Scope

This record covers the end-to-end Windows Setup run that validates the fix for
optional Docker timeouts in the first-run and onboarding path. The accepted
scope includes installation, the local Chat Bridge, profile onboarding, Persona
Layer control, profile compilation, Reflection and Governor behavior, a
confirmed diary write, and the Trashcan and deletion-protection rules.

## 2. Test Environment

| Property | Value |
| --- | --- |
| Target system | Windows 11 test VM |
| Test account | `UserTest` |
| Browser | Google Chrome with PLwC Chat Bridge |
| Setup | `PLwC-Setup-0.2.0-rc18.dev10-installer-r14.exe` |
| Gateway | `0.2.0-rc18.dev10` |
| Node Bridge | `0.2.0-rc19.dev20` |
| Browser Extension | `0.2.0-rc19.dev20` |
| Native Launcher | `0.2.0-rc19.dev20` |
| Active profile | `default` |

Setup artifact:

```text
File:   PLwC-Setup-0.2.0-rc18.dev10-installer-r14.exe
Bytes:  5,178,624
SHA256: 1817eb1efd2c5616d239fa83321bb8de4de35e133d8d960568b20ac96e6ef54f
```

## 3. Initial Condition

Before the fix, `plwc_status(scope="first_run")` failed on the VM when
`docker.exe info` exceeded its five-second timeout. Docker is optional for the
tested PLwC path. The timeout therefore must not prevent governed profile
onboarding.

## 4. Acceptance Matrix

| ID | Test | Expected Result | Status |
| --- | --- | --- | --- |
| AP-01 | Setup and component identity | Gateway reports dev10; Bridge components remain aligned on dev20; eight public tools are available. | PASS |
| AP-02 | First run without required Docker | An optional Docker failure does not abort first-run status, and onboarding can complete. | PASS |
| AP-03 | Profile onboarding and activation | `default` is created, activated, and resolved by PLwC from `plwc_state`. | PASS |
| AP-04 | Bridge Persona Layer switch | `persona_layer_disabled=true` disables and `false` enables the Persona Layer after `Save & Restart`. | PASS |
| AP-05 | Complete profile compilation | Full compile contains `CORE`, `TEMPERAMENT`, `PERSONA`, and `MEMORY`; transport and reconstruction are complete. | PASS |
| AP-06 | Reflection write | A confirmed entry changes only `reflection.md` and becomes a Memory candidate. | PASS |
| AP-07 | Governor threshold | A one-time observation is not promoted to `memory.md` without sufficient independent evidence. | PASS |
| AP-08 | Diary write | Explicit confirmation creates exactly the requested file under `Tagebuch/`. | PASS |
| AP-09 | Trashcan and deletion protection | Permanent deletion remains unavailable; an explicitly confirmed move to `Trashcan/` succeeds. | PASS |

## 5. Observed Runtime Results

### 5.1 Runtime and Profile

After onboarding, runtime status reported:

- `active_profile_name: default`
- `active_profile_source: plwc_state`
- `active_profile_status: ok`
- `profile_valid: true`
- `profile_runtime_available: true`
- missing required profile files: `0`
- public tools: `8/8`
- workspace structure: complete
- setup warnings: none
- Gateway version: `0.2.0rc18.dev10`

*Screenshot verified locally and retained outside the public repository.*

The formerly blocking first-run path therefore completed on the same VM and
reached a valid, active profile.

### 5.2 Persona Layer

The inverted Bridge setting was tested in both directions. With
`Persona layer disabled: true`, the layer was disabled. After changing the
value to `false` and selecting `Save & Restart`, runtime status reported:

- `persona_layer_enabled: true`
- source: `shared_config`

*Both Persona Layer screenshots were verified locally and are retained outside
the public repository.*

### 5.3 Full Compile

The full compile of profile `default` succeeded. The Persona Layer was active,
Governance and Hard Gates remained intact, and no profile file changed. Both
transport chunks arrived completely, and the reconstructed SHA-256 matched the
source. The layer contained `CORE`, `TEMPERAMENT`, `PERSONA`, and `MEMORY`.

*Screenshot verified locally and retained outside the public repository.*

### 5.4 Reflection and Governor

The Reflection workflow first proposed a confirmation-bound entry. After
approval, only `reflection.md` changed:

- `accepted: true`
- `duplicate_noop: false`
- evidence role: `new_insight`
- candidate and target: `memory.md`

*Both Reflection screenshots were verified locally and are retained outside
the public repository.*

The following Governor plan correctly stopped promotion:

- candidates: `1`
- eligible: `0`
- decision: `no_op`
- reason: `insufficient_evidence`
- threshold: `2`
- threshold source: `shared_config`
- `memory.md`: unchanged

*Screenshot verified locally and retained outside the public repository.*

A `force` call was neither required nor justified.

### 5.5 Diary

After explicit confirmation, PLwC created
`Tagebuch/2026-08-08_PLwC-Onboarding.md`. The entry records Setup, onboarding,
Persona Layer, compile, Reflection, and the effective Governance thresholds.
This step did not change unrelated files.

*Screenshot verified locally and retained outside the public repository.*

### 5.6 Trashcan and Deletion Protection

A move to a missing subdirectory failed without PLwC inventing a destination
directory or replacement name. A direct move of the disposable test file then
succeeded. When permanent deletion was requested, PLwC refused the operation
and offered an explicitly confirmed move to `Trashcan/` instead.

*Screenshot verified locally and retained outside the public repository.*

The move to `Trashcan/wegwer.txt` succeeded, and the source under `Temp/` was no
longer present.

*Screenshot verified locally and retained outside the public repository.*

## 6. Automated Prerequisite Verification

The following suites passed before manual VM acceptance:

```text
Gateway:                   45 passed, 6 skipped
Node Bridge:               23 passed
Browser Extension:        140 passed
Windows Setup (Pester):    62 passed, 0 failed
Setup UI smoke:            German and English PASS
```

The six Gateway skips require Docker-backed or symlink-capable system
conditions and are not failed tests.

## 7. Notes and Exclusions

- `Qdrant` was disabled. This optional feature was outside the acceptance scope
  and does not affect the result.
- Profile `default` is new. Its small Memory and Reflection footprint is
  expected.
- Any future Memory promotion still requires independent evidence dates.
- Browser-store distribution of the extension is a separate release topic.
- This acceptance validates the tested Windows, Chrome, and Bridge path. It
  does not automatically approve other operating systems or browser stores.

## 8. Final Disposition

Package `SETUP-P0-02-FIX-04`, consisting of Gateway `0.2.0-rc18.dev10`, Windows
Setup `installer-r14`, and Chat Bridge `0.2.0-rc19.dev20`, passed the manual
end-to-end run on the preserved Windows VM.

The previously open manual VM gate for the Docker onboarding fix is
**closed**. The scope documented in this record is **accepted**.

## 9. Privately Retained Screenshot Evidence

The screenshots contain a disposable VM account path, browser-session UI, and
a non-public chat locator. They are therefore excluded from the public
repository. Their hashes preserve the local evidence binding:

| File | SHA-256 |
| --- | --- |
| `01-runtime-profile-active.png` | `b32b03ec66fe8bd3528bf14f74e69d1f5728518c84f1109400df8604086ca059` |
| `02-persona-setting-disabled.png` | `1e1673e7b468a391f8be0540c631bbec0e1a8e8a1c0cb4e527e2fc93487c2358` |
| `03-persona-active-shared-config.png` | `6ef7f5a0e39b367267b723c5dba404780fa90af41df922f7c5ea6cf19cd68e56` |
| `04-profile-compile-full.png` | `8535f3ba4f825529a4e6808a80a6a14482e105fdbe0228452297b37e126b2da9` |
| `05-reflection-proposal.png` | `797f4ac4595742b53211211b770025f4271ab6061381d653d6bb47221a30995a` |
| `06-reflection-written.png` | `cd9fb52eed52a9c2aa5a8fb3af27c45829ac4321dc4e1d505515afdc66446b19` |
| `07-governor-insufficient-evidence.png` | `3356ef805886597ee505e9d8c45bc53c1f393681793de3e52689c4b3086fb3d2` |
| `08-diary-written.png` | `c385af85be4f780eb90f881f20fbf941f590beccab131adc817243f251407762` |
| `09-delete-refused-trashcan-offered.png` | `9daab43f1ac47894b38bb3e4f134116dd09a71193cc1dee7e77a224523637638` |
| `10-trashcan-move-succeeded.png` | `2d74b7fff57bb5fc8407ef0d51e265bda5bd5a78b0eb78b6b139fe2d3cbd2026` |
