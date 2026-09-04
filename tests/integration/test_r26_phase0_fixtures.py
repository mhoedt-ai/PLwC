from __future__ import annotations

import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "windows"


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_clean_and_dirty_windows_cases_are_distinct_and_preserve_user_data() -> None:
    clean = _load("r26-clean-install.json")
    dirty = _load("r26-dirty-r25-install.json")

    assert clean["classification"] == "clean"
    assert dirty["classification"] == "dirty_migrated"
    assert clean["expected"]["install_mode"] == "clean"  # type: ignore[index]
    assert dirty["expected"]["install_mode"] == "migration_required"  # type: ignore[index]
    assert clean["expected"]["user_data_preserved"] is True  # type: ignore[index]
    assert dirty["expected"]["user_data_preserved"] is True  # type: ignore[index]


def test_dirty_case_distinguishes_evidenced_plwc_state_from_foreign_port_owner() -> None:
    dirty = _load("r26-dirty-r25-install.json")
    processes = dirty["processes"]

    assert isinstance(processes, list)
    assert any(process["classification"] == "plwc_legacy_evidenced" for process in processes)
    assert any(process["classification"] == "foreign" for process in processes)
    assert dirty["port_3007"]["classification"] == "foreign"  # type: ignore[index]
    assert dirty["expected"]["foreign_processes_terminated"] == 0  # type: ignore[index]
    assert dirty["expected"]["port_conflict_blocks_apply"] is True  # type: ignore[index]
