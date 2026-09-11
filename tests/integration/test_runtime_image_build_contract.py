from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_lock_has_exact_three_digest_pinned_builds() -> None:
    lock = json.loads((ROOT / "docker" / "runtime-image-sources.json").read_text(encoding="utf-8"))
    assert lock["target_platform"] == "linux/amd64"
    assert [image["id"] for image in lock["images"]] == ["document_worker", "node_runner", "python_runner"]
    assert [image["repository"] for image in lock["images"]] == [
        "ghcr.io/mhoedt-ai/plwc-document-worker",
        "ghcr.io/mhoedt-ai/plwc-node-runner",
        "ghcr.io/mhoedt-ai/plwc-python-runner",
    ]
    for image in lock["images"]:
        assert re.fullmatch(r"docker\.io/library/.+@sha256:[0-9a-f]{64}", image["base"])


def test_every_runtime_dockerfile_is_pinned_and_labelled() -> None:
    for path in sorted((ROOT / "docker").glob("*-runner/Dockerfile")) + [ROOT / "docker" / "document-worker" / "Dockerfile"]:
        text = path.read_text(encoding="utf-8")
        assert re.match(r"^FROM [^\s]+@sha256:[0-9a-f]{64}$", text.splitlines()[0])
        assert ":latest" not in text
        for label in (
            "org.opencontainers.image.source",
            "org.opencontainers.image.version",
            "org.opencontainers.image.licenses",
            "org.opencontainers.image.created",
            "org.opencontainers.image.revision",
        ):
            assert label in text


def test_document_worker_build_is_offline_for_python_and_snapshot_locked_for_apt() -> None:
    text = (ROOT / "docker" / "document-worker" / "Dockerfile").read_text(encoding="utf-8")
    assert "PIP_NO_INDEX=1" in text
    assert "pip install --no-index" in text
    assert "--require-hashes" in text
    assert "snapshot.debian.org" in text
    assert "/var/cache/ldconfig/*" in text
    assert "/var/log/dpkg.log" in text
    install_block = text.split("apt-get install", 1)[1].split("&& rm", 1)[0]
    packages = [
        line.strip().rstrip(" \\")
        for line in install_block.splitlines()
        if line.strip() and not line.strip().startswith("-")
    ]
    assert packages and all("=" in package for package in packages)


def test_node_runner_exposes_node_but_removes_package_managers() -> None:
    text = (ROOT / "docker" / "node-runner" / "Dockerfile").read_text(encoding="utf-8")
    assert "/usr/local/lib/node_modules/npm" in text
    assert "/usr/local/lib/node_modules/corepack" in text
    assert "/opt/yarn-v1.22.22" in text
    for executable in ("npm", "npx", "corepack", "yarn", "yarnpkg"):
        assert f"/usr/local/bin/{executable}" in text


def test_every_runtime_image_removes_incidental_perl_runtime() -> None:
    paths = sorted((ROOT / "docker").glob("*-runner/Dockerfile")) + [
        ROOT / "docker" / "document-worker" / "Dockerfile"
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "dpkg --purge --force-remove-essential --force-depends perl-base" in text
        assert "test ! -e /usr/bin/perl" in text
        assert "! dpkg-query -W perl-base" in text
        assert "rm -f /var/log/dpkg.log" in text


def test_build_script_has_no_push_or_registry_login_path() -> None:
    path = ROOT / "scripts" / "build_runtime_images.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert tree is not None
    assert "docker push" not in text
    assert "docker login" not in text
    assert '"push"' not in text
    assert "--no-cache" in text
    assert "--platform" in text and "linux/amd64" in text
    assert "type=docker" in text and "rewrite-timestamp=true" in text
    assert 'observed.get("Id") not in {digest, config_digest}' in text
    assert '("docker", "load", "--input"' in text
    assert "Non-reproducible image build" in text
    assert '"source_clean": source_clean' in text
    assert "def _probe_image" in text
    assert '"--pull",' in text and '"never",' in text
    assert '"--network",' in text and '"none",' in text
    assert "npm npx corepack yarn yarnpkg" in text
    assert "test ! -e /usr/bin/perl" in text
    assert "! command -v perl" in text
    assert "! command -v tiffcrop" in text
    assert "ssl.OPENSSL_VERSION_INFO == (3, 5, 0, 7, 0)" in text
    assert "VEX_DOCUMENTS" in text
    assert 'evidence["vex"]' in text


def test_tiff_exception_is_narrow_openvex_evidence() -> None:
    path = ROOT / "security" / "vex" / "document-worker-CVE-2026-52490.openvex.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["@context"] == "https://openvex.dev/ns/v0.2.0"
    assert len(payload["statements"]) == 1
    statement = payload["statements"][0]
    assert statement["vulnerability"]["name"] == "CVE-2026-52490"
    assert statement["status"] == "not_affected"
    assert statement["justification"] == "vulnerable_code_not_present"
    assert statement["products"] == [
        {
            "@id": "pkg:docker/mhoedt-ai/plwc-document-worker@0.1.0",
            "subcomponents": [
                {
                    "@id": "pkg:deb/debian/tiff@4.7.0-3%2Bdeb13u3?os_distro=trixie&os_name=debian&os_version=13"
                }
            ],
        }
    ]
    assert "tiffcrop" in statement["impact_statement"]


def test_wheelhouse_builder_and_worker_acceptance_test_exist() -> None:
    builder = ROOT / "scripts" / "build_document_worker_wheelhouse.py"
    assert builder.is_file()
    builder_text = builder.read_text(encoding="utf-8")
    assert '"--require-hashes"' in builder_text
    assert '"--no-deps"' in builder_text
    assert "VENDORED_WHEELHOUSE" in builder_text
    assert "_write_outputs" not in builder_text
    assert "manylinux_2_28_x86_64" in builder_text
    refresher = ROOT / "scripts" / "refresh_document_worker_wheelhouse_lock.py"
    assert refresher.is_file()
    refresher_text = refresher.read_text(encoding="utf-8")
    assert "--accept-mutable-resolution" in refresher_text
    assert "_write_outputs" in refresher_text
    assert (ROOT / "scripts" / "verify_runtime_images.py").is_file()
    assert (ROOT / "scripts" / "finalize_runtime_image_manifest.py").is_file()
    assert (ROOT / "tests" / "integration" / "test_document_worker_mvp.py").is_file()


def test_registry_staging_workflow_is_manual_pinned_and_commit_scoped() -> None:
    path = ROOT / ".github" / "workflows" / "runtime-images.yml"
    text = path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert not re.search(r"(?m)^\s{2}(?:push|pull_request|schedule):", text)
    assert "PUBLISH_PRIVATE_R27_STAGING" in text
    assert "environment: r27-runtime-images-staging" in text
    assert "GHCR_STAGING_PAT" in text
    assert "secrets.GITHUB_TOKEN" not in text
    assert "plwc-r27-private-staging" in text
    assert "docker/staging-bootstrap" in text
    assert "packages: write" not in text
    assert text.index("Bootstrap absent private GHCR package shells") < text.index(
        "Push reproducible commit-scoped staging tags directly with BuildKit"
    )
    assert "r27-staging-${GITHUB_SHA::12}" in text
    assert "python scripts/push_runtime_images.py" in text
    assert "staging-push-report.json" in text
    assert "docker image push \"${repository}:0.1.0\"" not in text
    assert "public" not in text.casefold().replace("publish_private", "")
    uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in uses)


def test_public_promotion_workflow_is_manual_digest_locked_and_anonymously_verified() -> None:
    path = ROOT / ".github" / "workflows" / "runtime-images-public.yml"
    text = path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert not re.search(r"(?m)^\s{2}(?:push|pull_request|schedule):", text)
    assert "PROMOTE_APPROVED_R27_IMAGES" in text
    assert "VERIFY_PUBLIC_R27_IMAGES" in text
    assert "1d8eaa4f82c2aec2fbe7212d446c7ebb05fa9fe8" in text
    for digest in (
        "9f06960d30bc91701161d5490c24611f4e630ee8d0ab57eef04c6f7862df93e1",
        "fccb8cc036d24c764504749d802674e6e6f3c9c72726334b73aa674830e7b6f2",
        "83d7d224abbd287fab225a8d81c29b98795440af75edad3a70bf5f4b0c6278bc",
        "af6757f5fb28204b7f61b7076cad00fbe4e0a71e11276db5067419083718a6df",
        "9a8a4a3c78c9f8896b0370e033b56b742b1227e03e7d711630399164e399ee7d",
        "95fdfdbd4a5f1f67d3a485a773e5e7a4e9b73295f78fad70a5407f8519dd5917",
    ):
        assert digest in text
    assert "--prefer-index=false" in text
    assert "Premature public visibility" in text
    assert 'printf \'{"auths":{}}\\n\'' in text
    assert 'export DOCKER_CONFIG="$anonymous_config"' in text
    assert 'docker pull "$reference"' in text
    assert 'docker image inspect "$reference"' in text
    assert "expected_repo_digest" in text
    assert "docker buildx build" not in text
    assert "docker push" not in text
    assert "packages: write" not in text
    uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in uses)


def test_direct_staging_push_uses_buildkit_registry_export_and_exact_identity_gate() -> None:
    text = (ROOT / "scripts" / "push_runtime_images.py").read_text(encoding="utf-8")
    assert "type=registry,name=" in text
    assert "rewrite-timestamp=true" in text
    assert "--no-cache" in text
    assert "--provenance=false" in text
    assert "--sbom=false" in text
    assert 'digest != image["digest"]' in text
    assert 'config_digest != image["config_digest"]' in text
    assert "docker image push" not in text


def test_staging_bootstrap_cannot_link_private_packages_to_the_source_repository() -> None:
    text = (ROOT / "docker" / "staging-bootstrap" / "Dockerfile").read_text(encoding="utf-8")
    assert text.splitlines()[0] == "FROM scratch"
    assert "org.opencontainers.image.source" not in text
