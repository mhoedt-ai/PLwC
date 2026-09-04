from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


INVENTORY_SCHEMA_VERSION = "1.0.0"
STATUS_VALUES = {
    "ready",
    "compatible",
    "recommended_update",
    "required_update",
    "missing",
    "optional",
    "unknown",
    "mixed_installation",
}
TRUST_VALUES = {
    "verified_local",
    "observed_local",
    "trusted_release",
    "unverified",
    "unavailable",
}
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class InventoryContractError(ValueError):
    """Raised when compatibility or inventory input violates the shared contract."""


@dataclass(frozen=True)
class _SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> _SemanticVersion:
        match = _SEMVER_PATTERN.fullmatch(value)
        if match is None:
            raise InventoryContractError(f"Invalid semantic version: {value!r}.")
        prerelease = match.group("prerelease")
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            tuple(prerelease.split(".")) if prerelease else (),
        )

    def compare(self, other: _SemanticVersion) -> int:
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return -1 if core < other_core else 1
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_numeric = left.isdigit()
            right_numeric = right.isdigit()
            if left_numeric and right_numeric:
                return -1 if int(left) < int(right) else 1
            if left_numeric != right_numeric:
                return -1 if left_numeric else 1
            return -1 if left < right else 1
        if len(self.prerelease) == len(other.prerelease):
            return 0
        return -1 if len(self.prerelease) < len(other.prerelease) else 1


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InventoryContractError(f"{label} must be an object.")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InventoryContractError(f"{label} must be non-empty text.")
    return value.strip()


def _validate_matrix(matrix: Mapping[str, Any]) -> None:
    if matrix.get("schema_version") != INVENTORY_SCHEMA_VERSION:
        raise InventoryContractError("Unsupported compatibility-matrix schema version.")
    _require_nonempty_string(matrix.get("matrix_version"), "matrix_version")
    _require_nonempty_string(matrix.get("release_family"), "release_family")

    status_model = _require_mapping(matrix.get("status_model"), "status_model")
    if set(status_model) != STATUS_VALUES:
        raise InventoryContractError("Compatibility matrix must define the complete status model.")
    for status, value in status_model.items():
        entry = _require_mapping(value, f"status_model.{status}")
        _require_nonempty_string(entry.get("action"), f"status_model.{status}.action")

    trust_model = matrix.get("trust_model")
    if not isinstance(trust_model, list) or set(trust_model) != TRUST_VALUES:
        raise InventoryContractError("Compatibility matrix must define the complete trust model.")

    components = matrix.get("components")
    if not isinstance(components, list) or not components:
        raise InventoryContractError("Compatibility matrix components must be a non-empty array.")
    identifiers: list[str] = []
    for index, raw_component in enumerate(components):
        component = _require_mapping(raw_component, f"components[{index}]")
        identifier = _require_nonempty_string(component.get("id"), f"components[{index}].id")
        _require_nonempty_string(component.get("display_name"), f"components[{index}].display_name")
        if type(component.get("required")) is not bool:
            raise InventoryContractError(f"components[{index}].required must be boolean.")
        identifiers.append(identifier)
        semantic = component.get("semantic_version")
        if semantic is not None:
            semantic_policy = _require_mapping(semantic, f"components[{index}].semantic_version")
            for key in ("minimum", "maximum_exclusive"):
                if semantic_policy.get(key) is not None:
                    _SemanticVersion.parse(_require_nonempty_string(semantic_policy[key], key))
        protocol = component.get("protocol")
        if protocol is not None:
            protocol_policy = _require_mapping(protocol, f"components[{index}].protocol")
            _require_nonempty_string(protocol_policy.get("name"), "protocol.name")
            versions = protocol_policy.get("supported_versions")
            if not isinstance(versions, list) or not versions:
                raise InventoryContractError("protocol.supported_versions must be non-empty.")
            for version in versions:
                _SemanticVersion.parse(_require_nonempty_string(version, "protocol version"))
    if len(set(identifiers)) != len(identifiers):
        raise InventoryContractError("Compatibility-matrix component identifiers must be unique.")


def load_compatibility_matrix(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryContractError(f"Compatibility matrix could not be read safely: {exc}") from exc
    matrix = _require_mapping(value, "compatibility matrix")
    _validate_matrix(matrix)
    return dict(matrix)


def version_in_policy(version: str, policy: Mapping[str, Any]) -> bool:
    parsed = _SemanticVersion.parse(version)
    minimum = policy.get("minimum")
    maximum_exclusive = policy.get("maximum_exclusive")
    if minimum is not None and parsed.compare(_SemanticVersion.parse(str(minimum))) < 0:
        return False
    if maximum_exclusive is not None and parsed.compare(_SemanticVersion.parse(str(maximum_exclusive))) >= 0:
        return False
    return True


def _source(value: Any, *, fallback_trust: str = "unavailable") -> dict[str, Any]:
    if value is None:
        return {"kind": "none", "trust": fallback_trust, "observed_at": None}
    source = _require_mapping(value, "component source")
    trust = _require_nonempty_string(source.get("trust"), "component source trust")
    if trust not in TRUST_VALUES:
        raise InventoryContractError(f"Unsupported component source trust: {trust!r}.")
    return {
        "kind": _require_nonempty_string(source.get("kind"), "component source kind"),
        "trust": trust,
        "observed_at": source.get("observed_at") if isinstance(source.get("observed_at"), str) else None,
        **({"detail": source["detail"]} if isinstance(source.get("detail"), str) else {}),
    }


def _normalized_identity(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "semantic_version": observation.get("semantic_version") if isinstance(observation.get("semantic_version"), str) else None,
        "protocol_version": observation.get("protocol_version") if isinstance(observation.get("protocol_version"), str) else None,
        "build_revision": observation.get("build_revision") if isinstance(observation.get("build_revision"), str) else None,
        "build_identity_schema": (
            observation.get("build_identity_schema")
            if type(observation.get("build_identity_schema")) is int
            else None
        ),
        "build_id": observation.get("build_id") if isinstance(observation.get("build_id"), str) else None,
        "sha256": observation.get("sha256") if isinstance(observation.get("sha256"), str) else None,
        "source": _source(observation.get("source")),
    }


def _contract_view(component: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "semantic_version": component.get("semantic_version"),
        "protocol": component.get("protocol"),
        "build_identity": component.get("build_identity"),
        "readiness": component.get("readiness"),
    }


def _available_view(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    available = _require_mapping(value, "available component release")
    semantic_version = _require_nonempty_string(available.get("semantic_version"), "available semantic_version")
    _SemanticVersion.parse(semantic_version)
    update_kind = available.get("update_kind", "recommended")
    if update_kind not in {"recommended", "required"}:
        raise InventoryContractError("available update_kind must be recommended or required.")
    return {
        "semantic_version": semantic_version,
        "build_revision": available.get("build_revision") if isinstance(available.get("build_revision"), str) else None,
        "build_id": available.get("build_id") if isinstance(available.get("build_id"), str) else None,
        "sha256": available.get("sha256") if isinstance(available.get("sha256"), str) else None,
        "update_kind": update_kind,
        "source": _source(available.get("source"), fallback_trust="unverified"),
    }


def _result(
    component: Mapping[str, Any],
    installed: Mapping[str, Any],
    available: Mapping[str, Any] | None,
    status: str,
    reasons: list[str],
    status_model: Mapping[str, Any],
) -> dict[str, Any]:
    compatible: bool | None
    if status in {"ready", "compatible", "recommended_update"}:
        compatible = True
    elif status in {"required_update", "missing", "mixed_installation"}:
        compatible = False
    else:
        compatible = None
    action = _require_mapping(status_model[status], f"status_model.{status}").get("action")
    return {
        "id": component["id"],
        "display_name": component["display_name"],
        "required": component["required"],
        "installed": dict(installed),
        "contract": _contract_view(component),
        "available": dict(available) if available is not None else None,
        "status": status,
        "compatible": compatible,
        "reasons": reasons,
        "action": action,
    }


def classify_component(
    component: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
    *,
    available: Mapping[str, Any] | None,
    status_model: Mapping[str, Any],
) -> dict[str, Any]:
    observed = observation or {}
    installed = _normalized_identity(observed)
    available_view = _available_view(available)
    required = bool(component["required"])

    active_paths = observed.get("active_paths")
    distinct_paths = {
        str(path).strip().casefold()
        for path in active_paths
        if str(path).strip()
    } if isinstance(active_paths, list) else set()
    if observed.get("mixed_installation") is True or len(distinct_paths) > 1:
        return _result(
            component,
            installed,
            available_view,
            "mixed_installation",
            ["multiple_active_runtime_paths"],
            status_model,
        )

    present = observed.get("present")
    if present is False:
        status = "missing" if required else "optional"
        return _result(component, installed, available_view, status, ["component_not_detected"], status_model)
    if present is not True:
        return _result(
            component,
            installed,
            available_view,
            "unknown",
            ["component_presence_unknown"],
            status_model,
        )

    incompatible: list[str] = []
    incomplete: list[str] = []
    semantic_policy = component.get("semantic_version")
    if isinstance(semantic_policy, Mapping):
        semantic_version = installed["semantic_version"]
        if semantic_version is None:
            if semantic_policy.get("required", True) is True:
                incomplete.append("semantic_version_unknown")
        else:
            try:
                supported_semantic_version = version_in_policy(semantic_version, semantic_policy)
            except InventoryContractError:
                incompatible.append("semantic_version_invalid")
            else:
                if not supported_semantic_version:
                    incompatible.append("semantic_version_outside_supported_range")

    protocol_policy = component.get("protocol")
    if isinstance(protocol_policy, Mapping):
        protocol_version = installed["protocol_version"]
        if protocol_version is None:
            if protocol_policy.get("required", True) is True:
                incomplete.append("protocol_version_unknown")
        elif protocol_version not in protocol_policy.get("supported_versions", []):
            incompatible.append("protocol_version_not_supported")

    identity_policy = component.get("build_identity")
    if isinstance(identity_policy, Mapping) and identity_policy.get("required", False) is True:
        schema = installed["build_identity_schema"]
        schemas = identity_policy.get("supported_schema_versions", [])
        if schema is None:
            incomplete.append("build_identity_schema_unknown")
        elif schema not in schemas:
            incompatible.append("build_identity_schema_not_supported")
        if identity_policy.get("build_id_required", False) is True and installed["build_id"] is None:
            incomplete.append("build_id_unknown")
        if identity_policy.get("sha256_required", False) is True:
            sha256 = installed["sha256"]
            if sha256 is None:
                incomplete.append("sha256_unknown")
            elif re.fullmatch(r"[a-fA-F0-9]{64}", sha256) is None:
                incompatible.append("sha256_invalid")

    readiness = component.get("readiness")
    if isinstance(readiness, Mapping):
        required_tool_count = readiness.get("required_tool_count")
        if type(required_tool_count) is int:
            tool_count = observed.get("tool_count")
            if type(tool_count) is not int:
                incomplete.append("tool_count_unknown")
            elif tool_count != required_tool_count:
                incompatible.append("tool_count_mismatch")
        if readiness.get("canonical_tools_required", False) is True:
            canonical = observed.get("canonical_tools_valid")
            if canonical is None:
                incomplete.append("canonical_tool_set_unknown")
            elif canonical is not True:
                incompatible.append("canonical_tool_set_invalid")

    if incompatible:
        return _result(component, installed, available_view, "required_update", incompatible, status_model)
    if incomplete:
        return _result(component, installed, available_view, "unknown", incomplete, status_model)

    status = "ready" if observed.get("postflight_verified") is True else "compatible"
    reasons = ["all_required_contracts_match"]
    if available_view is not None and available_view["source"]["trust"] == "trusted_release":
        installed_version = installed["semantic_version"]
        if installed_version is not None:
            comparison = _SemanticVersion.parse(installed_version).compare(
                _SemanticVersion.parse(str(available_view["semantic_version"]))
            )
            if comparison < 0:
                if available_view["update_kind"] == "required":
                    status = "required_update"
                    reasons = ["trusted_required_update_available"]
                else:
                    status = "recommended_update"
                    reasons = ["trusted_recommended_update_available"]
    elif available_view is not None:
        reasons.append("available_release_untrusted")

    return _result(component, installed, available_view, status, reasons, status_model)


def build_component_inventory(
    matrix: Mapping[str, Any],
    observations: Mapping[str, Mapping[str, Any]],
    *,
    available_releases: Mapping[str, Mapping[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    _validate_matrix(matrix)
    components = matrix["components"]
    component_ids = {str(component["id"]) for component in components}
    unknown_observations = set(observations) - component_ids
    if unknown_observations:
        raise InventoryContractError(
            "Inventory observations contain unknown components: " + ", ".join(sorted(unknown_observations))
        )
    releases = available_releases or {}
    unknown_releases = set(releases) - component_ids
    if unknown_releases:
        raise InventoryContractError(
            "Available releases contain unknown components: " + ", ".join(sorted(unknown_releases))
        )
    timestamp = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    status_model = _require_mapping(matrix["status_model"], "status_model")
    inventory = [
        classify_component(
            component,
            observations.get(str(component["id"])),
            available=releases.get(str(component["id"])),
            status_model=status_model,
        )
        for component in components
    ]
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "matrix_version": matrix["matrix_version"],
        "release_family": matrix["release_family"],
        "generated_at": timestamp,
        "components": inventory,
        "summary": {
            status: sum(1 for component in inventory if component["status"] == status)
            for status in sorted(STATUS_VALUES)
        },
    }
