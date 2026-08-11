from __future__ import annotations

from plwc_gateway.adapters import pba


def _reflection_entry(*, index: int, date: str, content: str) -> dict[str, str]:
    return {
        "candidate_for": "memory.md",
        "content": content,
        "date": date,
        "entry_id": f"entry-{index}",
        "evidence": f"{date}: test evidence",
        "marker": "Muster",
        "trust": "hoch",
    }


def test_compacted_reflection_memory_plan_keeps_review_relevant_skips_visible() -> None:
    skipped = [
        pba._reflection_memory_skip(
            _reflection_entry(index=index, date="2026-07-06", content=f"Old processed candidate {index}"),
            "already_processed",
            "Reflection entry was already processed.",
        )
        for index in range(50)
    ]
    skipped.append(
        pba._reflection_memory_skip(
            _reflection_entry(
                index=51,
                date="2026-07-27",
                content=(
                    "Mirco expects mature Wandorra work to check source status, test status "
                    "and design intent before suggesting more expansion."
                ),
            ),
            "insufficient_evidence",
            "Only 1 distinct evidence date(s); required evidence count is 2 for classification 'inferred_observation'.",
        )
    )

    compact = pba._compact_skipped_candidates({
        "plan_id": "plan-1",
        "skipped_candidates": skipped,
        "eligible_candidate_ids": [],
    })

    assert "skipped_candidates" not in compact
    assert list(compact).index("skipped_candidates_preview") < list(compact).index("eligible_candidate_ids")
    assert compact["skipped_candidate_count"] == 51
    assert compact["skipped_candidates_summary"] == {
        "already_processed": 50,
        "insufficient_evidence": 1,
    }
    assert compact["skipped_candidates_preview_count"] == 1
    assert compact["skipped_candidates_preview_omitted"] == 0
    assert compact["skipped_candidates_preview"] == [
        {
            "original_index": 50,
            "entry_id": "entry-51",
            "date": "2026-07-27",
            "decision": "insufficient_evidence",
            "reason": (
                "Only 1 distinct evidence date(s); required evidence count is 2 "
                "for classification 'inferred_observation'."
            ),
            "candidate_for": "memory.md",
            "marker": "Muster",
            "trust": "hoch",
            "candidate_summary": (
                "Mirco expects mature Wandorra work to check source status, test status "
                "and design intent before suggesting more expansion."
            ),
        }
    ]
