# Windows Setup P1-02 Acceptance Evidence

Date: 2026-08-08

Scope: `SETUP-P1-02` only. This package adds the post-install Getting Started
experience and advances Windows Setup to `installer-r15`. Gateway
`0.2.0-rc18.dev10` and Chat Bridge `0.2.0-rc19.dev20` remain unchanged.

## Purpose

The accepted r14 VM run showed that installation and governed workflows work
end to end, but Setup opened only a technical installation summary. New users
still needed a concise operational guide covering the Bridge Primer and the
most frequently repeated PLwC workflows before browser-store distribution.

## Implemented Contract

Setup installs self-contained English and German HTML guides plus one local
stylesheet under `app/docs`. The explicit Setup language selects the guide
opened by default on the Finish page and the guide targeted by the Start menu.
The diagnostic installation summary remains available as a separate unchecked
Finish action.

The guide makes the Bridge startup order explicit:

```text
Status -> 8 / 8 -> Primer -> Generate -> Insert Bridge Primer -> manual send
```

It states that users describe work in normal language after inserting the
Primer. Natural-language examples are paired with expected public PLwC calls
for verification, while `plwc_describe` remains the required schema-discovery
path when the AI is uncertain.

Covered workflows:

- first-run status and governed profile onboarding;
- boot, working, and full compile modes with Persona Layer control;
- Reflection candidate writes and separate Governor promotion;
- Governor plan, review, explicit confirmation, and apply;
- confirmed diary writes and no background journaling;
- confirmed moves to `Trashcan/` instead of deletion;
- diary scan and governed Persona promotion with source provenance;
- narrow, journaled `force` behavior that cannot bypass quality or security
  gates;
- Windows restart, extension reload, Bridge restart, and reconnect guidance.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| English and German local guides | PASS | Both source pages share the explicit `SETUP-P1-02` contract marker and one responsive local stylesheet. |
| No remote content or telemetry | PASS | Contract tests reject external URLs, scripts, and remote stylesheet assets. |
| Localized Finish action | PASS (source/UI contract) | Inno selects the page through `ActiveLanguage`; the guide action is selected by default. Exact post-install opening remains in the VM gate below. |
| Persistent Start menu access | PASS (source/UI contract) | The localized Start menu entry targets the same language-aware path. Exact installed-link execution remains in the VM gate below. |
| Keep diagnostics separate | PASS | Installation summary remains present and is explicitly `unchecked`. |
| Primer and natural-language guidance | PASS | Tests require `Generate`, `Insert Bridge Primer`, manual send, natural-language instructions, and `plwc_describe` instead of guessed calls. |
| Required workflow coverage | PASS | Tests require onboarding, compile, Reflection, Governor, diary, Trashcan, Persona promotion, Force, and restart terms and calls. |
| Stage and package the exact pages | PASS | All three assets are staged under `common/docs` and included in the SHA-256 payload manifest. |
| Bind Setup r15 identity | PASS | Installer source, artifact name, payload manifest, external identity, and evidence package consistently use r15/P1-02. |

## Verification

Automated verification completed on 2026-08-08:

- Gateway: `45 passed`, `6 skipped`.
- Node Bridge: `23 passed`, `0 failed`.
- Browser Extension: `140 passed`, `0 failed`.
- Windows installer Pester suite: `64 passed`, `0 failed`.
- Focused Getting Started and clean-machine UI contracts: `45 passed`,
  `0 failed`.
- Guarded production UI smoke, English: passed all 10 wizard pages and stopped
  on `Install` before installation.
- Guarded production UI smoke, German: passed all 10 wizard pages and stopped
  on `Installieren` before installation.
- `git diff --check` for the task-owned source and documentation files: pass.

Production artifact:

```text
installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r15.exe
Size: 5,186,584 bytes
SHA-256: 235badd95a809b3e6b403d82dd16aef4e6341aba916c014946e224d3409be5f7
```

The external build identity records the same executable hash and binds:

```text
Gateway:           0.2.0-rc18.dev10
Node Bridge:       0.2.0-rc19.dev20
Browser Extension: 0.2.0-rc19.dev20
Native Launcher:   0.2.0-rc19.dev20
Evidence package:  SETUP-P1-02
```

Payload manifest:

```text
Artifact: PLwC-0.2.0-rc18.dev10-payload-manifest.json
SHA-256: 7660531399b7c260cb8c119b2b28db49fc843e91bd3e6c3a5ef057905e78458f
Payload size: 17,520,942 bytes
```

Packaged guide records:

```text
common/docs/getting-started-en.html
  12,970 bytes
  39a8e07332bfdf5d050dbb0c3a29d4e96c722a70867a769b210da8c33e6896a2
common/docs/getting-started-de.html
  14,050 bytes
  f0ead46124199b2d5db9ff36a82fee89b4c57cfbfe8c83867a53b6a8f2083c3d
common/docs/getting-started.css
  4,607 bytes
  0ac079746786affc4620319cf67c42664b71cbfbda48bfe70b77f4e9de687a62
```

## Remaining Gate

The exact r15 executable requires one preserved-VM Finish-page check confirming
that the language-matched guide opens, renders locally, and remains available
from the Start menu. The already accepted r14 runtime workflows do not need to
be repeated unless the installation changes their component identities.
