# r27 Runtime Images – Local Verification

Date: 2026-09-06

Status: **PARTIAL PASS / G3 remains STOP**

This record covers only the clean local reproducibility and offline-probe
portion of G3. It is not a release approval, registry publication, public-image
claim or production-installer build.

## Source and report

- Source commit: `437af257b57460374aa39864720bcf9b2eac5833`
- Git source state observed by the build script: clean
- Local report: `build/runtime-images-437af25/image-build-report.json`
- Report SHA-256: `65cf60fbba5b91c8b76e03120fd82911c16ed2d5cfee6926c563fc3843f63c4f`
- Report status: `development_only`, exclusively because Docker Scout CVE
  scanning required a Docker Hub authentication that was not supplied
- Independent report verification with the explicit development-only switch:
  PASS

## Reproducible identities

Each image was built twice with `--no-cache` for `linux/amd64`. BuildKit's OCI
exporter rewrote layer timestamps to the source commit epoch. Both the image
manifest digest and image configuration digest matched between rounds.

| Image | Manifest digest, both rounds | Config digest, both rounds | Local content bytes |
| --- | --- | --- | ---: |
| Document Worker | `sha256:01722dfe2f77f365f5a16b2ad31ff1225eba63cccfe3472dea46157de4a10903` | `sha256:451daba353ddd14b627d354508506cdf0ae8eb1197517e6e4dc287c7c801ae07` | 206708880 |
| Node Runner | `sha256:3e0c14506e8b8c12980364c3c60688d156377564e5f000e6c237d263101d8cb2` | `sha256:953163ac172d5126394de975e432e208bb3dd6f4dcd9fae7e51a5c9627f1b439` | 79890220 |
| Python Runner | `sha256:bfc4ca4cf2dd68b211a2b7424521656f50d422ad46acfb3ae9a4cdf1c1450305` | `sha256:932b3bf8e68bac066a935c308ae3454a99b5c00c869aa10353d0e03340d1f642` | 45430577 |

These are local build identities only. They are not approved installer-lock
digests until the private GHCR staging copy has been scanned, pushed and read
back without identity drift.

## Evidence and probes

- SPDX SBOM: generated for all three images
- Licence inventory: generated for all three images
- Local SLSA-shaped provenance: generated for all three images
- CVE report: unavailable; release-grade verification therefore correctly
  remains closed
- Document Worker fixed import probe: PASS for all ten locked capabilities
- Node Runner hardened offline probe: PASS, `v22.22.3`
- Python Runner hardened offline probe: PASS, `Python 3.12.13`
- Document Worker creation/ZIP MVP suite: `6 passed`
- Probe constraints: `--pull never`, `--network none`, read-only root,
  capability drop, no-new-privileges, PID/memory/CPU limits and fixed UID

## Remaining G3 blockers

1. Run the approved authenticated Docker Scout CVE scan and reject every
   unaccepted HIGH/CRITICAL result.
2. Obtain explicit Product Owner approval for the private GHCR staging push.
3. Push only commit-scoped staging tags, read both registry manifest and config
   digests back, and require exact agreement with the clean local build.
4. Generate and reverify the final digest-only installer manifest from that
   staging evidence.
