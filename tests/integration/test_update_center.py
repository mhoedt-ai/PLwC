from __future__ import annotations

import base64
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from plwc_gateway.installation.update_center import (
    MAX_MANIFEST_BYTES,
    UpdateCenter,
    UpdateConfirmationRequired,
    UpdateFetchError,
    UpdateSecurityError,
    canonical_manifest_bytes,
    parse_manifest_json,
    verify_release_manifest,
)


ARTIFACT = base64.b64decode("UEx3QyByMjYgc2lnbmVkIGFydGlmYWN0IGZpeHR1cmUNCg==")
TEST_KEY_ID = "r26-test-only"
TEST_TRUSTED_KEYS = {
    TEST_KEY_ID: {
        "exponent": 65537,
        "modulus": int(
            "bcfdcd2ad3b67e0462a79e20eb80ef769d999408ca5c34599c4ceaf1f23aba10"
            "1dbd83d78cb3a752cf65bfea5dc9cc1e5505de817663ddfeffa1949fe6795baa1"
            "be20307e758c26cb7c4ff8c4b1c2d67526319fcc9fa89602428dbca2985b742af"
            "33c2ab3115606aa1525787e6f803181410b1ee46ee5768f6fa87afcaed7d3495e"
            "c3c45e854d405c3ea09a0dd37f9ff6f47d9d7fca08af982f2856fca345b0544e"
            "46f2ac6e80d801a357fc5f1ea0cd000ad19ff013c015a456feacde5118c280e55"
            "d917c0c9a4fc0a3fbfcb82fae6172ef4f1446cf76f3d022c29124f35537718118"
            "697086500f2a926306a4fc34ba254a1c47059cab9aa6ade547cae354ded",
            16,
        ),
    }
}
SIGNATURE = (
    "ErUDfAto4HwdjTpZnQtdsbsSSs9j3ZuB7QCjEaEbpWHoB4N+OE4LK0+wAV6y6p3A"
    "t3GTWPaJLrdtoG9bN1dMxBj7Pa3Vi7Tq4fmLShOT2pkGsL8FkN2XhcV8K/nFzVeG"
    "xMR5EYsinBzoQMhdYayQ765DmYKH/UGVAxr2dEhoGxbyleMLSTCeWqZYYo32W7/jM"
    "ko8SYSjQatVlJ3dfqgZyIsd7j/+BqWTu0696nVU2RimVN2whDIStsDQKFDOB3zlij"
    "cRtqNJSTi/8L8nLsv8YMP4ie8NYwIFs3b74oEc4lhQ3Jp9f6mYGjVbo+HdeqDq/9"
    "p/wAMFyqw0kp2kTo70rQ=="
)
MANIFEST_URL = "https://updates.example.invalid/plwc-release-manifest.json"
ARTIFACT_URL = "https://updates.example.invalid/PLwC-Setup-1.0.0-installer-r26.exe"


def signed_manifest() -> dict[str, object]:
    digest = "9817cccdef34917e8d281154355cb32dad2bd9e7d6a09d20897296b4cf98ca2b"
    return {
        "schema_version": "1.0.0",
        "product": {"name": "PLwC", "version": "1.0.0", "installer_revision": "installer-r26"},
        "release": {
            "published_at": "2026-09-03T10:00:00+00:00",
            "update_kind": "recommended",
            "notes": {"de": "Sichere Testfreigabe.", "en": "Secure test release."},
        },
        "components": [
            {
                "id": "gateway",
                "version": "1.0.0",
                "compatibility": {"minimum": "1.0.0", "maximum_exclusive": "1.1.0"},
            },
            {
                "id": "browser_extension",
                "version": "1.0.1",
                "compatibility": {"minimum": "1.0.0", "maximum_exclusive": "1.1.0"},
            },
        ],
        "artifacts": [
            {
                "id": "windows_installer",
                "kind": "windows_installer",
                "file_name": "PLwC-Setup-1.0.0-installer-r26.exe",
                "url": ARTIFACT_URL,
                "size": len(ARTIFACT),
                "sha256": digest,
                "build_identity": {
                    "schema_version": 1,
                    "build_id": f"plwc@1.0.0/installer-r26#sha256:{digest}",
                    "product_version": "1.0.0",
                    "installer_revision": "installer-r26",
                    "sha256": digest,
                },
            }
        ],
        "signature": {
            "algorithm": "rsa-sha256-pkcs1v15",
            "key_id": TEST_KEY_ID,
            "value_base64": SIGNATURE,
        },
    }


def manifest_bytes(manifest: dict[str, object] | None = None) -> bytes:
    return json.dumps(manifest or signed_manifest(), ensure_ascii=False, sort_keys=True).encode("utf-8")


class FixtureFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.offline = False
        self.artifact = ARTIFACT
        self.manifest = manifest_bytes()

    def __call__(self, url: str, maximum_bytes: int) -> bytes:
        self.calls.append(url)
        if self.offline:
            raise UpdateFetchError("offline fixture")
        payload = self.manifest if url == MANIFEST_URL else self.artifact
        assert len(payload) <= maximum_bytes
        return payload


def test_signed_manifest_verifies_and_canonical_form_excludes_only_signature() -> None:
    manifest = parse_manifest_json(manifest_bytes())
    verified = verify_release_manifest(manifest, TEST_TRUSTED_KEYS)

    assert verified["product"]["installer_revision"] == "installer-r26"
    assert len(verified["components"]) == 2
    assert b'"signature"' not in canonical_manifest_bytes(verified)


def test_tampered_or_untrusted_manifest_is_rejected() -> None:
    tampered = signed_manifest()
    tampered["release"]["update_kind"] = "required"

    with pytest.raises(UpdateSecurityError, match="signature verification failed"):
        verify_release_manifest(tampered, TEST_TRUSTED_KEYS)
    with pytest.raises(UpdateSecurityError, match="untrusted key"):
        verify_release_manifest(signed_manifest(), {})


def test_duplicate_json_members_and_non_https_artifacts_fail_closed() -> None:
    with pytest.raises(Exception, match="Duplicate JSON member"):
        parse_manifest_json(b'{"schema_version":"1.0.0","schema_version":"1.0.0"}')
    unsafe = copy.deepcopy(signed_manifest())
    unsafe["artifacts"][0]["url"] = "http://updates.example.invalid/setup.exe"
    with pytest.raises(UpdateSecurityError):
        verify_release_manifest(unsafe, TEST_TRUSTED_KEYS)


def test_check_is_interval_limited_and_offline_keeps_last_verified_result(tmp_path: Path) -> None:
    now = [datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)]
    fetcher = FixtureFetcher()
    center = UpdateCenter(
        state_root=tmp_path / "state",
        manifest_url=MANIFEST_URL,
        trusted_keys=TEST_TRUSTED_KEYS,
        fetch_bytes=fetcher,
        clock=lambda: now[0],
    )

    current = center.check()
    assert current["state"] == "update_available"
    assert current["update_kind"] == "recommended"
    assert current["integrity_verified"] is True
    assert current["check_due"] is False
    assert fetcher.calls == [MANIFEST_URL]

    assert center.check()["state"] == "update_available"
    assert fetcher.calls == [MANIFEST_URL]

    now[0] += timedelta(hours=7)
    fetcher.offline = True
    offline = center.check()
    assert offline["state"] == "offline"
    assert offline["cached_release_available"] is True
    assert offline["last_valid_at"] == current["last_valid_at"]
    assert offline["last_checked_at"] != offline["last_valid_at"]


def test_tampered_live_manifest_never_replaces_verified_cache(tmp_path: Path) -> None:
    fetcher = FixtureFetcher()
    center = UpdateCenter(
        state_root=tmp_path / "state",
        manifest_url=MANIFEST_URL,
        trusted_keys=TEST_TRUSTED_KEYS,
        fetch_bytes=fetcher,
    )
    center.check(force=True)
    cached_before = center.manifest_path.read_bytes()
    tampered = signed_manifest()
    tampered["product"]["installer_revision"] = "installer-r99"
    fetcher.manifest = manifest_bytes(tampered)

    rejected = center.check(force=True)

    assert rejected["state"] == "rejected"
    assert rejected["integrity_verified"] is False
    assert rejected["cached_release_available"] is True
    assert center.manifest_path.read_bytes() == cached_before


def test_download_and_install_require_separate_confirmation_and_reverify_hash(tmp_path: Path) -> None:
    fetcher = FixtureFetcher()
    state_root = tmp_path / "state"
    center = UpdateCenter(
        state_root=state_root,
        manifest_url=MANIFEST_URL,
        trusted_keys=TEST_TRUSTED_KEYS,
        fetch_bytes=fetcher,
    )
    center.check(force=True)
    plan = center.plan_download("windows_installer")

    with pytest.raises(UpdateConfirmationRequired, match="download"):
        center.download(plan["plan_id"], confirmed=False)
    assert fetcher.calls == [MANIFEST_URL]

    downloaded = center.download(plan["plan_id"], confirmed=True)
    assert downloaded["state"] == "download_verified"
    assert Path(downloaded["artifact_path"]).read_bytes() == ARTIFACT

    runner_calls: list[Path] = []
    with pytest.raises(UpdateConfirmationRequired, match="installation"):
        center.install(plan["plan_id"], confirmed=False, runner=lambda path: 0)
    assert runner_calls == []

    completed = center.install(
        plan["plan_id"],
        confirmed=True,
        runner=lambda path: runner_calls.append(path) or 0,
    )
    assert completed["state"] == "installer_completed"
    assert completed["build_identity_verified"] is True
    assert runner_calls == [Path(downloaded["artifact_path"])]


@pytest.mark.parametrize("artifact", [b"x" * len(ARTIFACT), ARTIFACT[:-1]])
def test_wrong_hash_or_interrupted_download_is_rejected_and_not_installed(
    tmp_path: Path,
    artifact: bytes,
) -> None:
    fetcher = FixtureFetcher()
    center = UpdateCenter(
        state_root=tmp_path / "state",
        manifest_url=MANIFEST_URL,
        trusted_keys=TEST_TRUSTED_KEYS,
        fetch_bytes=fetcher,
    )
    center.check(force=True)
    plan = center.plan_download("windows_installer")
    fetcher.artifact = artifact

    with pytest.raises(UpdateSecurityError, match="size|hash"):
        center.download(plan["plan_id"], confirmed=True)

    assert not list(center.download_root.glob("*.exe"))
    assert not list(center.download_root.glob("*.part"))


def test_failed_installer_surfaces_existing_r26_rollback_report(tmp_path: Path) -> None:
    fetcher = FixtureFetcher()
    state_root = tmp_path / "state"
    center = UpdateCenter(
        state_root=state_root,
        manifest_url=MANIFEST_URL,
        trusted_keys=TEST_TRUSTED_KEYS,
        fetch_bytes=fetcher,
    )
    center.check(force=True)
    plan = center.plan_download("windows_installer")
    center.download(plan["plan_id"], confirmed=True)
    rollback_report = state_root / "installer-r26" / "last-failure.json"
    rollback_report.parent.mkdir(parents=True)
    rollback_report.write_text('{"rollback":"completed"}\n', encoding="utf-8")

    failed = center.install(plan["plan_id"], confirmed=True, runner=lambda _path: 1603)

    assert failed["ok"] is False
    assert failed["state"] == "installer_failed"
    assert failed["return_code"] == 1603
    assert failed["rollback_report"] == str(rollback_report)
