"""RC8-FEAT-002 — Qdrant retrieval index (Phase 1 boundary slice).

A *reconstructable semantic retrieval index over governed sources* — no own
memory source, no source of truth. Design + acceptance criteria: see
``docs/RC9_QDRANT_PHASE0_DESIGN.md`` and ``docs/RC8_BRIEFING.md`` §2 / RC8-FEAT-002.

**Boundary (do not soften):**
- OFF by default. Enabled only via the governance flag ``qdrant_enabled``.
- Backends (``fastembed``, ``qdrant-client``) are an optional extra and are
  **imported lazily** — never at module import time, never on the hot path.
- The embedding model is **pinned in code**: no library default, **no automatic
  fallback**. If the pinned model is unavailable or its dimension is not 384,
  PLwC stops with a clear error rather than silently using another model.
- No background process / watcher. ``reindex`` is always explicit.
- No Qdrant hit becomes behaviorally active without a governed Plan/Apply.

Phase plan (this file is Phase 1 — skeleton + pinned config + lazy import +
model verification + metadata):
- Phase 2: build/index governed sections (v1 source: ``memory.md`` only),
  ACTIVE/RETIRED payload, canonical-SHA + fingerprint + embedding-id meta.
- Phase 3: ``retrieve`` (read) — full output contract + staleness enforcement +
  ``require_fresh`` + default retired-exclusion.
- Phase 4: ``reindex`` / ``drop_index`` operations under the existing facades.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as _importlib_metadata
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pinned configuration (exact — no library default, no automatic fallback)
# ---------------------------------------------------------------------------

EMBEDDING_BACKEND = "FastEmbed"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

#: Pinned backend distribution versions (mirror of pyproject's [qdrant] extra).
FASTEMBED_PINNED_VERSION = "0.8.0"
QDRANT_CLIENT_PINNED_VERSION = "1.18.0"

#: Index storage lives under the active workspace root (local mode, CPU, no Docker).
QDRANT_STORAGE_SUBDIR = "qdrant_storage"

#: v1 indexed sources (Q3). Controlled expansion to PERSONA.md / TEMPERAMENT.md
#: comes later; reflection.md only much later and marked non-authoritative.
QDRANT_SOURCES_V1: tuple[str, ...] = ("memory.md",)

#: Governance flag (flat key in governance/config.yaml; OFF when absent).
QDRANT_ENABLED_KEY = "qdrant_enabled"


# ---------------------------------------------------------------------------
# Errors — every failure is explicit; none triggers a fallback model.
# ---------------------------------------------------------------------------


class QdrantError(RuntimeError):
    """Base class for all Qdrant retrieval-index errors."""


class QdrantFeatureDisabled(QdrantError):
    """Raised when a Qdrant operation is requested while qdrant_enabled is false."""


class QdrantBackendUnavailable(QdrantError):
    """Raised when the optional fastembed / qdrant-client backends are not installed."""


class QdrantModelUnavailable(QdrantError):
    """Raised when the pinned embedding model is not in the backend's registry.

    Never falls back to another model — the caller must stop.
    """


class QdrantDimensionMismatch(QdrantError):
    """Raised when the pinned model's embedding dimension is not EMBEDDING_DIM."""


# ---------------------------------------------------------------------------
# Feature gate
# ---------------------------------------------------------------------------


def qdrant_enabled(governance_values: dict[str, str] | None) -> bool:
    """Return True only when governance/config.yaml sets qdrant_enabled truthy.

    Absent key ⇒ False (feature OFF by default).
    """
    if not governance_values:
        return False
    raw = str(governance_values.get(QDRANT_ENABLED_KEY, "")).strip().casefold()
    return raw in {"true", "yes", "1", "on"}


# ---------------------------------------------------------------------------
# Lazy backend import (never at module load, never on the hot path)
# ---------------------------------------------------------------------------


def _import_backends() -> tuple[Any, Any]:
    """Import (fastembed, qdrant_client) lazily.

    Raises QdrantBackendUnavailable with an install hint if the optional extra
    is not present.
    """
    try:
        import fastembed  # type: ignore
        import qdrant_client  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise QdrantBackendUnavailable(
            "Qdrant retrieval index requires the optional backends. Install them "
            "with: pip install 'plwc-gateway[qdrant]' "
            f"(pinned: fastembed=={FASTEMBED_PINNED_VERSION}, "
            f"qdrant-client=={QDRANT_CLIENT_PINNED_VERSION})."
        ) from exc
    return fastembed, qdrant_client


# ---------------------------------------------------------------------------
# Pinned-model verification — no fallback
# ---------------------------------------------------------------------------


def _resolve_model_dimension(supported_models: list[dict[str, Any]]) -> int:
    """Pure check: the pinned model must be present with dimension EMBEDDING_DIM.

    Separated from the fastembed call so the no-fallback logic is testable
    without the backend installed (and without downloading any model).
    """
    by_name = {m.get("model"): m for m in supported_models}
    entry = by_name.get(EMBEDDING_MODEL)
    if entry is None:
        raise QdrantModelUnavailable(
            f"Pinned embedding model {EMBEDDING_MODEL!r} is not supported by the "
            f"installed {EMBEDDING_BACKEND} backend. PLwC does not fall back to "
            "another model — install a backend version that provides this exact "
            "model, or change the pin deliberately in code."
        )
    dim = entry.get("dim")
    if dim != EMBEDDING_DIM:
        raise QdrantDimensionMismatch(
            f"Pinned embedding model {EMBEDDING_MODEL!r} reports dimension {dim!r}, "
            f"expected {EMBEDDING_DIM}. PLwC stops rather than indexing at an "
            "unexpected dimension."
        )
    return EMBEDDING_DIM


def verify_embedding_model() -> int:
    """Verify the pinned model is available at the pinned dimension. No fallback.

    Returns the verified dimension (EMBEDDING_DIM) or raises a QdrantError. Reads
    the backend's model registry only — does not download the model.
    """
    fastembed, _qdrant_client = _import_backends()
    supported = list(fastembed.TextEmbedding.list_supported_models())
    return _resolve_model_dimension(supported)


def _backend_version() -> str:
    try:
        return _importlib_metadata.version("fastembed")
    except _importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


# ---------------------------------------------------------------------------
# Index metadata (written into the collection meta at reindex time)
# ---------------------------------------------------------------------------


def build_index_metadata(
    *,
    last_reindex: str,
    index_fingerprint: str,
    source_fingerprints: dict[str, str],
    backend_version: str | None = None,
) -> dict[str, Any]:
    """Assemble the index meta record (the required fields).

    - backend / backend_version / model / dimension — the embedding identity, so
      a model swap is detectable and retrieval is reproducible.
    - index_fingerprint — collection-level canon fingerprint.
    - last_reindex — when the index was (re)built.
    - source_fingerprints — canonical fingerprint per source/section.
    """
    return {
        "backend": EMBEDDING_BACKEND,
        "backend_version": backend_version if backend_version is not None else _backend_version(),
        "model": EMBEDDING_MODEL,
        "dimension": EMBEDDING_DIM,
        "index_fingerprint": index_fingerprint,
        "last_reindex": last_reindex,
        "source_fingerprints": dict(source_fingerprints),
    }


# ---------------------------------------------------------------------------
# Phase 2 — building index units from a governed source (pure, no backend)
# ---------------------------------------------------------------------------


#: Only real lifecycle sections are indexed; preamble headings like ``# Memory``
#: parse as status ``OTHER`` and are skipped.
INDEXABLE_STATUSES = frozenset({"ACTIVE", "RETIRED"})


@dataclass(frozen=True)
class IndexUnit:
    """One indexable canonical section of a governed source file."""

    source_file: str
    section_id: str            # the exact ``## ...`` heading line
    lifecycle_status: str      # ACTIVE | RETIRED
    profile: str
    text: str                  # heading + body, the text that is embedded/hashed
    source_sha256: str         # canonical SHA over ``text`` (LF-normalized)
    section_occurrence: int = 1
    section_duplicate_count: int = 1

    def legacy_unit_key(self) -> str:
        return f"{self.source_file}::{self.section_id}"

    def unit_key(self) -> str:
        base = self.legacy_unit_key()
        if self.section_duplicate_count <= 1:
            return base
        return f"{base}::occurrence={self.section_occurrence}"

    def fingerprint_identity(self) -> str:
        if self.section_duplicate_count <= 1:
            return f"{self.source_file}\x00{self.section_id}\x00{self.source_sha256}"
        return (
            f"{self.source_file}\x00{self.section_id}\x00"
            f"{self.section_occurrence}\x00{self.source_sha256}"
        )


def _section_text(heading: str, body: str) -> str:
    """Canonical section text = heading line + body, LF-normalized and stripped.

    ``read_text`` already normalizes CRLF→LF; this keeps the hash/embedding
    deterministic regardless of on-disk line endings (same principle as
    RC7-FIX-001 / RC8-UX-001 canonical SHA).
    """
    return f"{heading}\n{body}".strip()


def canonical_section_sha256(heading: str, body: str) -> str:
    return hashlib.sha256(_section_text(heading, body).encode("utf-8")).hexdigest()


def build_index_units(*, profile: str, source_file: str, text: str) -> list[IndexUnit]:
    """Parse a governed source file into indexable units.

    Reuses the canonical level-2 reader (``_parse_profile_entries``) so section
    semantics match retirement / compile exactly. Skips non-lifecycle headings.
    """
    from .pba import _parse_profile_entries  # local import: avoid load-time coupling

    parsed_entries = [
        entry
        for entry in _parse_profile_entries(text)
        if entry["status"] in INDEXABLE_STATUSES
    ]
    heading_counts: dict[str, int] = {}
    for entry in parsed_entries:
        heading = entry["heading"]
        heading_counts[heading] = heading_counts.get(heading, 0) + 1

    units: list[IndexUnit] = []
    heading_seen: dict[str, int] = {}
    for entry in parsed_entries:
        status = entry["status"]
        heading = entry["heading"]
        body = entry["body"]
        heading_seen[heading] = heading_seen.get(heading, 0) + 1
        units.append(
            IndexUnit(
                source_file=source_file,
                section_id=heading,
                lifecycle_status=status,
                profile=profile,
                text=_section_text(heading, body),
                source_sha256=canonical_section_sha256(heading, body),
                section_occurrence=heading_seen[heading],
                section_duplicate_count=heading_counts[heading],
            )
        )
    return units


def source_fingerprints(units: list[IndexUnit]) -> dict[str, str]:
    """Map ``source_file::section_id`` → canonical section SHA (per-section)."""
    return {u.unit_key(): u.source_sha256 for u in units}


def compute_index_fingerprint(units: list[IndexUnit]) -> str:
    """Collection-level fingerprint: SHA over the sorted per-section identities.

    Deterministic and order-independent; any added/removed/changed section flips
    it, which is what makes index staleness detectable at retrieve time.
    """
    parts = sorted(u.fingerprint_identity() for u in units)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mtime_seconds(path: Path) -> float | None:
    try:
        return path.stat().st_mtime if path.is_file() else None
    except OSError:
        return None


def _mtime_iso(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_diagnostics(*, memory_path: Path, storage_dir: Path, meta: dict[str, Any] | None) -> dict[str, Any]:
    source_mtime_seconds = _mtime_seconds(memory_path)
    meta_mtime_seconds = _mtime_seconds(storage_dir / INDEX_META_FILENAME)
    source_newer = (
        source_mtime_seconds is not None
        and meta_mtime_seconds is not None
        and source_mtime_seconds > meta_mtime_seconds
    )
    return {
        "last_indexed": meta.get("last_reindex") if isinstance(meta, dict) else None,
        "source_mtime": _mtime_iso(source_mtime_seconds),
        "index_meta_mtime": _mtime_iso(meta_mtime_seconds),
        "source_newer_than_index": source_newer if meta_mtime_seconds is not None else None,
    }


def _staleness_reason(
    *,
    memory_present: bool,
    index_stale: bool,
    model_mismatch: bool,
    changed_sources: list[dict[str, str]],
    source_newer_than_index: bool | None,
) -> str:
    if model_mismatch:
        return "model_mismatch"
    if not index_stale:
        return "fresh"
    if not memory_present:
        return "memory_missing"
    if changed_sources:
        return "memory_changed"
    if source_newer_than_index is True:
        return "memory_newer_than_index_meta"
    return "index_fingerprint_mismatch"


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_cosine_matrix(rows: list[str], cols: list[str]) -> list[list[float]]:
    """RC12-INNER-001 — cosine-similarity matrix between two small text lists using
    the pinned embedding model. Lazy backend; verifies the model (no fallback). Not
    a hot path (a few scanner clusters × a few ACTIVE entries). Returns rows×cols
    cosines; empty inputs yield an empty/short matrix."""
    if not rows or not cols:
        return [[0.0 for _ in cols] for _ in rows]
    fastembed, _ = _import_backends()
    verify_embedding_model()  # raises (no fallback) on missing model / wrong dim
    model = fastembed.TextEmbedding(model_name=EMBEDDING_MODEL)
    row_vecs = [list(map(float, v)) for v in model.embed(list(rows))]
    col_vecs = [list(map(float, v)) for v in model.embed(list(cols))]
    return [[_cosine(r, c) for c in col_vecs] for r in row_vecs]


# ---------------------------------------------------------------------------
# Phase 2 — backend-backed reindex engine (lazy; explicit; full rebuild)
# ---------------------------------------------------------------------------

#: Sidecar meta file written next to the Qdrant storage. Derived data only;
#: removed together with the index on drop. Read by retrieve for staleness.
INDEX_META_FILENAME = "index_meta.json"


def _collection_name(profile: str) -> str:
    return f"memory__{profile}"


def reindex_profile(
    *,
    profile: str,
    memory_path: Path,
    storage_dir: Path,
) -> dict[str, Any]:
    """Full, explicit rebuild of the retrieval index from ``memory.md``.

    Boundary: this is the only writer of the index; it never mutates the canon.
    No watcher — the caller invokes it explicitly. Verifies the pinned model
    (no fallback) before embedding. Reconstructable: it recreates the collection
    from scratch every time, so the index is a pure function of the canon.

    Returns a summary dict (counts + the meta record). v1 source: memory.md only.
    """
    fastembed, qdrant_client = _import_backends()
    dim = verify_embedding_model()  # raises (no fallback) on missing model / wrong dim

    text = memory_path.read_text(encoding="utf-8") if memory_path.is_file() else ""
    units = build_index_units(profile=profile, source_file="memory.md", text=text)

    storage_dir.mkdir(parents=True, exist_ok=True)
    from qdrant_client import models as qmodels  # type: ignore

    client = qdrant_client.QdrantClient(path=str(storage_dir))
    collection = _collection_name(profile)
    try:
        # Full rebuild: drop any prior collection, then recreate from scratch so
        # the index stays a pure function of the canon (reconstructable).
        if client.collection_exists(collection):
            client.delete_collection(collection)
        client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )

        if units:
            model = fastembed.TextEmbedding(model_name=EMBEDDING_MODEL)
            vectors = list(model.embed([u.text for u in units]))
            points = [
                qmodels.PointStruct(
                    id=i,
                    vector=list(map(float, vec)),
                    payload={
                        "source_file": u.source_file,
                        "section_id": u.section_id,
                        "lifecycle_status": u.lifecycle_status,
                        "profile": u.profile,
                        "source_sha256": u.source_sha256,
                        "section_key": u.unit_key(),
                        "section_occurrence": u.section_occurrence,
                        "section_duplicate_count": u.section_duplicate_count,
                        "text": u.text,
                    },
                )
                for i, (u, vec) in enumerate(zip(units, vectors))
            ]
            client.upsert(collection_name=collection, points=points)
    finally:
        client.close()

    meta = build_index_metadata(
        last_reindex=_utc_now_iso(),
        index_fingerprint=compute_index_fingerprint(units),
        source_fingerprints=source_fingerprints(units),
    )
    (storage_dir / INDEX_META_FILENAME).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "ok": True,
        "profile": profile,
        "collection": collection,
        "indexed_sections": len(units),
        "active_sections": sum(1 for u in units if u.lifecycle_status == "ACTIVE"),
        "retired_sections": sum(1 for u in units if u.lifecycle_status == "RETIRED"),
        "meta": meta,
    }


def load_index_meta(storage_dir: Path) -> dict[str, Any] | None:
    """Read the sidecar index meta, or None if the index has not been built."""
    meta_file = storage_dir / INDEX_META_FILENAME
    if not meta_file.is_file():
        return None
    return json.loads(meta_file.read_text(encoding="utf-8"))


def drop_index(*, profile: str, storage_dir: Path) -> dict[str, Any]:
    """Delete the derived index for a profile. Loses no canonical memory.

    The storage dir holds only derived data (vectors + meta sidecar), so it can
    be removed at any time; the canon (memory.md) is untouched and ``reindex``
    reconstructs the index. No background process.
    """
    import shutil

    existed = storage_dir.exists()
    if existed:
        shutil.rmtree(storage_dir)
    return {
        "ok": True,
        "operation": "drop_index",
        "profile": profile,
        "dropped": existed,
        "canon_preserved": True,
    }


# ---------------------------------------------------------------------------
# Phase 3 — retrieve (read-only) with the full staleness contract
# ---------------------------------------------------------------------------

#: source_current values for a hit (design §4.2).
SOURCE_CURRENT = "current"
SOURCE_CHANGED = "source_changed"
SOURCE_RETIRED = "source_retired"
SOURCE_MISSING = "source_missing"


def diff_changed_sources(
    indexed_fingerprints: dict[str, str], live_fingerprints: dict[str, str]
) -> list[dict[str, str]]:
    """Per-section diff between the indexed canon and the live canon.

    Returns a sorted list of ``{unit_key, change}`` where change is
    ``added`` / ``removed`` / ``changed`` (pure; no backend).
    """
    changes: list[dict[str, str]] = []
    for key in sorted(set(indexed_fingerprints) | set(live_fingerprints)):
        old = indexed_fingerprints.get(key)
        new = live_fingerprints.get(key)
        if old == new:
            continue
        if old is None:
            changes.append({"unit_key": key, "change": "added"})
        elif new is None:
            changes.append({"unit_key": key, "change": "removed"})
        else:
            changes.append({"unit_key": key, "change": "changed"})
    return changes


def _hit_source_current(
    *,
    section_key: str,
    hit_sha: str,
    live_by_key: dict[str, "IndexUnit"],
    memory_present: bool,
    legacy_section_key: str | None = None,
    live_by_legacy_key: dict[str, list["IndexUnit"]] | None = None,
) -> tuple[str, str | None]:
    """Classify a hit against the *live* canon. No hit is ``current`` unless its
    source file, heading/section and canonical SHA all match live.

    Returns ``(source_current, missing_reason)`` where missing_reason reuses the
    RC8-UX-001 distinction (``file_not_found`` / ``heading_not_found``) when the
    section can no longer be resolved.
    """
    live = live_by_key.get(section_key)
    if live is None and legacy_section_key and live_by_legacy_key is not None:
        candidates = live_by_legacy_key.get(legacy_section_key, [])
        for candidate in candidates:
            if candidate.source_sha256 == hit_sha:
                if candidate.lifecycle_status == "RETIRED":
                    return SOURCE_RETIRED, None
                return SOURCE_CURRENT, None
        if candidates:
            if all(candidate.lifecycle_status == "RETIRED" for candidate in candidates):
                return SOURCE_RETIRED, None
            return SOURCE_CHANGED, None
    if live is None:
        return SOURCE_MISSING, ("file_not_found" if not memory_present else "heading_not_found")
    if live.lifecycle_status == "RETIRED":
        return SOURCE_RETIRED, None
    if live.source_sha256 != hit_sha:
        return SOURCE_CHANGED, None
    return SOURCE_CURRENT, None


def retrieve(
    *,
    profile: str,
    query: str,
    memory_path: Path,
    storage_dir: Path,
    limit: int = 5,
    include_retired: bool = False,
    require_fresh: bool = False,
) -> dict[str, Any]:
    """Semantic retrieval over the index — read-only evidence, never authoritative.

    Always returns the staleness contract fields (last_reindex, index_stale,
    changed_sources, embedding_model, index_fingerprint) and, per hit,
    source_current + source_file + section_id + the hit's canonical SHA.

    Contract: a hit is reported ``current`` only when its own source/heading/SHA
    match the live canon. ``index_stale`` (collection-level) flags overall drift;
    with ``require_fresh=true`` a stale index refuses and returns no hits.
    Default retrieval excludes RETIRED; ``include_retired`` includes + marks them.
    A model identity different from the configured pin makes the index unusable
    (vectors not comparable) — no fallback, no hits.
    """
    meta = load_index_meta(storage_dir)
    source_diagnostics = _source_diagnostics(memory_path=memory_path, storage_dir=storage_dir, meta=meta)
    base: dict[str, Any] = {
        "ok": True,
        "operation": "retrieve",
        "profile": profile,
        "query": query,
        "require_fresh": require_fresh,
        "include_retired": include_retired,
        "embedding_model": EMBEDDING_MODEL,
        "hits": [],
    }
    if meta is None:
        return {**base, "indexed": False, "reason": "not_indexed",
                "last_reindex": None, "index_fingerprint": None,
                "index_stale": True, "changed_sources": [],
                **source_diagnostics,
                "staleness_reason": "not_indexed", "next_action": "reindex"}

    # Live canon snapshot (read-only).
    memory_present = memory_path.is_file()
    text = memory_path.read_text(encoding="utf-8") if memory_present else ""
    live_units = build_index_units(profile=profile, source_file="memory.md", text=text)
    live_by_key = {u.unit_key(): u for u in live_units}
    live_by_legacy_key: dict[str, list[IndexUnit]] = {}
    for unit in live_units:
        live_by_legacy_key.setdefault(unit.legacy_unit_key(), []).append(unit)
    live_fp = compute_index_fingerprint(live_units)
    live_source_fps = source_fingerprints(live_units)

    indexed_fp = meta.get("index_fingerprint")
    changed_sources = diff_changed_sources(meta.get("source_fingerprints", {}), live_source_fps)
    model_mismatch = meta.get("model") != EMBEDDING_MODEL or meta.get("dimension") != EMBEDDING_DIM
    index_stale = model_mismatch or (live_fp != indexed_fp)
    staleness_reason = _staleness_reason(
        memory_present=memory_present,
        index_stale=index_stale,
        model_mismatch=model_mismatch,
        changed_sources=changed_sources,
        source_newer_than_index=source_diagnostics.get("source_newer_than_index"),
    )

    contract = {
        **base,
        "indexed": True,
        "last_reindex": meta.get("last_reindex"),
        **source_diagnostics,
        "index_fingerprint": indexed_fp,
        "live_fingerprint": live_fp,
        "index_stale": index_stale,
        "changed_sources": changed_sources,
        "staleness_reason": staleness_reason,
        "next_action": "reindex" if index_stale else "none",
    }

    # Model mismatch ⇒ stored vectors are not comparable. No fallback, no hits.
    if model_mismatch:
        return {**contract, "hits": [], "reason": "model_mismatch",
                "indexed_model": meta.get("model"), "indexed_dimension": meta.get("dimension")}

    # require_fresh gate: a stale index refuses rather than returning marked-stale hits.
    if require_fresh and index_stale:
        return {**contract, "hits": [], "reason": "refused_stale", "refused_stale": True}

    # Backend search (lazy).
    fastembed, qdrant_client = _import_backends()
    from qdrant_client import models as qmodels  # type: ignore

    model = fastembed.TextEmbedding(model_name=EMBEDDING_MODEL)
    query_vec = list(map(float, next(iter(model.embed([query])))))

    query_filter = None
    if not include_retired:
        query_filter = qmodels.Filter(
            must_not=[qmodels.FieldCondition(
                key="lifecycle_status", match=qmodels.MatchValue(value="RETIRED"))]
        )

    client = qdrant_client.QdrantClient(path=str(storage_dir))
    try:
        response = client.query_points(
            collection_name=_collection_name(profile),
            query=query_vec,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        scored = response.points
    finally:
        client.close()

    hits = []
    for point in scored:
        payload = point.payload or {}
        legacy_section_key = f"{payload.get('source_file')}::{payload.get('section_id')}"
        section_key = str(payload.get("section_key") or legacy_section_key)
        source_current, missing_reason = _hit_source_current(
            section_key=section_key,
            hit_sha=payload.get("source_sha256", ""),
            live_by_key=live_by_key,
            memory_present=memory_present,
            legacy_section_key=legacy_section_key,
            live_by_legacy_key=live_by_legacy_key,
        )
        hit = {
            "score": float(point.score),
            "source_file": payload.get("source_file"),
            "section_id": payload.get("section_id"),
            "lifecycle_status": payload.get("lifecycle_status"),
            "source_sha256": payload.get("source_sha256"),
            "source_current": source_current,
            "text": payload.get("text"),
        }
        if payload.get("section_key") is not None:
            hit["section_key"] = payload.get("section_key")
        if payload.get("section_occurrence") is not None:
            hit["section_occurrence"] = payload.get("section_occurrence")
        if missing_reason is not None:
            hit["missing_reason"] = missing_reason
        hits.append(hit)

    return {**contract, "hits": hits}
