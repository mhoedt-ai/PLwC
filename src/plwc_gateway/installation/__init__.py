"""Installed-component inventory and compatibility contracts for PLwC."""

from .component_inventory import (
    INVENTORY_SCHEMA_VERSION,
    InventoryContractError,
    build_component_inventory,
    classify_component,
    load_compatibility_matrix,
    version_in_policy,
)
from .doctor import (
    ALLOWED_REPAIR_ACTIONS,
    DOCTOR_SCHEMA_VERSION,
    REPAIR_PLAN_SCHEMA_VERSION,
    DoctorContractError,
    InstallationDoctor,
    STABLE_CHAT_BRIDGE_EXTENSION_ID,
    collect_windows_system_facts,
)
from .installer_state import (
    INSTALLER_MIGRATION_PLAN_VERSION,
    INSTALLER_STATE_SCHEMA_VERSION,
    InstallerStateEngine,
    InstallerStateError,
)
from .update_center import (
    UpdateCenter,
    UpdateConfirmationRequired,
    UpdateContractError,
    UpdateSecurityError,
    canonical_manifest_bytes,
    load_trusted_release_keys,
    parse_manifest_json,
    verify_release_manifest,
)

__all__ = [
    "INVENTORY_SCHEMA_VERSION",
    "InventoryContractError",
    "build_component_inventory",
    "classify_component",
    "load_compatibility_matrix",
    "version_in_policy",
    "ALLOWED_REPAIR_ACTIONS",
    "DOCTOR_SCHEMA_VERSION",
    "REPAIR_PLAN_SCHEMA_VERSION",
    "DoctorContractError",
    "InstallationDoctor",
    "STABLE_CHAT_BRIDGE_EXTENSION_ID",
    "collect_windows_system_facts",
    "INSTALLER_MIGRATION_PLAN_VERSION",
    "INSTALLER_STATE_SCHEMA_VERSION",
    "InstallerStateEngine",
    "InstallerStateError",
    "UpdateCenter",
    "UpdateConfirmationRequired",
    "UpdateContractError",
    "UpdateSecurityError",
    "canonical_manifest_bytes",
    "load_trusted_release_keys",
    "parse_manifest_json",
    "verify_release_manifest",
]
