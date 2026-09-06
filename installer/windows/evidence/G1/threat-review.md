# G1 threat review - r27 runtime image delivery

Date: 2026-09-05

Status: **PASS AT DESIGN LEVEL**

## Threats and required controls

| Threat | Impact | Mandatory control | Verification gate |
| --- | --- | --- | --- |
| Mutable tag changes after review | Unreviewed code executes | pull and run complete `repository@sha256:` only; tags display only | G2, G3, G4, G6 |
| Registry/repository substitution | Attacker-controlled image | schema allowlists `ghcr.io/mhoedt-ai` and exactly three repositories | G2, G4 |
| Wrong architecture or manifest | failed/foreign runtime | require `linux/amd64` in lock and post-pull inspect | G2, G4, G5 |
| Local tag shadows intended image | stale/malicious local execution | inspect/run exact digest; ignore friendly tag | G2, G4 |
| Digest or payload-lock tampering | bypass of approved artifact | payload SHA-256 plus schema validation before any pull | G3, G4 |
| Registry credential leakage | account compromise | anonymous public pull only; no login/token/config write; redact process data | G2, G4, G5 |
| Workflow compromise | malicious published artifact | SHA-pin actions, minimal permissions, protected manual approval, provenance bound to commit | G3, G6 |
| Mutable base or Debian mirror | irreproducible/vulnerable build | digest-pin bases; fixed snapshot and exact package/version lock | G2, G3 |
| Dependency confusion/network pip | hostile Python package | offline wheelhouse, exact versions and hashes, no runtime install | G3, G4 |
| Known critical vulnerability | unsafe released image | SBOM, licence inventory and scanner policy; fail unaccepted critical/high finding | G3, G6 |
| Forged or stale provenance | false source claim | verify subject digest, source repository and commit against registry digest | G3, G6 |
| Pull succeeds but image cannot run | false readiness | real hardened networkless probe for every image | G4, G5 |
| Probe reaches network or gains privilege | data exfiltration/host risk | `--network none`, non-root, read-only, cap-drop, no-new-privileges, resource/time limits | G2, G4 |
| Partial pull/disk exhaustion | inconsistent state | precheck free space, per-image state/report, safe-mode result, idempotent retry | G2, G4, G5 |
| Docker daemon absent/restarting | hang or false success | named-pipe/daemon timeout, bounded retries only after user action, Safe Mode | G2, G4, G5 |
| Proxy/DNS/TLS failure | unusable install | stable categorized error, report, no success claim, new-click retry | G2, G4, G5 |
| User cancellation ignored | unwanted download | cancellable owned child, no automatic restart, persist `cancelled` | G2, G4, G5 |
| Shell/argument injection | arbitrary command execution | Python argument arrays, no shell, commands/refs only from validated manifest | G2, G4 |
| Untrusted stdout/log escape or secret | diagnostic injection/leak | UTF-8 replacement, size cap, control-character normalization and redaction | G2, G4 |
| Unexpected Python exception | missing report like r26 | outer `Exception` catch and atomic fallback report; report-existence check in Inno | G2, G4, G5 |
| Broad rollback/cleanup | data or shared-layer loss | only owned file transaction; no automatic image/layer deletion | G2, G4, G5 |
| TOCTOU after inspect | different runtime executed | execute the same immutable digest reference, then record resulting container image ID | G4 |
| Runtime network pull | drift after setup | retain `--pull never` and `--network none`; no runtime login/pull path | G2, G4 |

## Trust decisions

- GitHub/GHCR transport is trusted only to deliver bytes matching the locked
  digest; a tag or HTTP success is not evidence.
- The local Docker daemon is a required privileged dependency. PLwC does not
  claim protection from a malicious daemon, but it detects absence, timeout,
  wrong platform and observed digest mismatch.
- The committed build workflow is not self-approving. Package push, public
  visibility and final production build remain human approval boundaries.
- Scanner results do not replace reproducibility, SBOM, provenance or runtime
  hardening. All are conjunctive release evidence.

## Residual risks accepted for G1

- A public anonymous GHCR endpoint can be unavailable or blocked by enterprise
  policy; r27 remains usable in explicit Safe Mode and reports this honestly.
- Docker may retain downloaded shared layers after cancellation or uninstall;
  automatic deletion is more dangerous than this storage residue.
- Upstream security databases can change after a build; G6 records scan time
  and policy, and later updates require a new locked image digest.

No residual risk permits tag-only execution, hidden download, credential use,
unreported failure, data deletion or a false full-readiness claim.

Decision: no unmitigated severity-1/2 design threat remains. **A-SEC design
review PASS**, subject to the explicit G2/G3/G4/G5 tests above.
