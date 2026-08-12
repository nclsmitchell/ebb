import hashlib
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from ebb import __version__ as ENGINE_VERSION  # noqa: N812
from ebb.canonicalize import canonicalize
from ebb.detect.base import RawMatch
from ebb.finding import Evidence, Finding, FindingState, ProductCode, Verdict
from ebb.owner import find_owner
from ebb.registry.loader import Registry
from ebb.registry.models import RegistryEntry
from ebb.registry.resolve import Resolution, Resolved, resolve
from ebb.verdict import compute_confidence, compute_severity, compute_verdict
from ebb.walk import scan_repo

RULE_ID = "ebb.retirement"


def compute_identity(canonical_id: str, relative_path: str, symbol: str) -> str:
    """Canonical model id + file path + normalized surrounding symbol — deliberately excludes
    the line number, per SUITE_ARCHITECTURE.md §3.1: identity must survive cosmetic reformatting
    and break on real change. A hash rather than a readable string because identity is compared,
    never displayed — title/detail_md carry the human-facing description."""
    raw = f"ebb|{canonical_id}|{relative_path}|{symbol}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _title_for(canonical_id: str, verdict: Verdict, entry: RegistryEntry | None) -> str:
    if verdict is Verdict.BREAK:
        assert entry is not None and entry.shutdown_at is not None
        return f"{canonical_id} retired {entry.shutdown_at.isoformat()}"
    if verdict is Verdict.DRIFT:
        assert entry is not None and entry.shutdown_at is not None
        return f"{canonical_id} retires {entry.shutdown_at.isoformat()}"
    if verdict is Verdict.CLEAR:
        return f"{canonical_id} is actively supported"
    return f"{canonical_id} is not in the tracked registry"


def _detail_md_for(canonical_id: str, entry: RegistryEntry | None) -> str:
    if entry is None:
        return (
            f"`{canonical_id}` was detected but is not a verified entry in the retirement "
            "registry. This means unknown, not confirmed safe."
        )
    parts = [f"Provider: **{entry.provider.value}**", f"Source: {entry.source_url}"]
    if entry.announced_at:
        parts.append(f"Announced: {entry.announced_at.isoformat()}")
    if entry.shutdown_at:
        parts.append(f"Shutdown: {entry.shutdown_at.isoformat()}")
    if entry.replacement_id:
        parts.append(f"Replacement: `{entry.replacement_id}`")
    return "\n".join(f"- {p}" for p in parts)


def build_finding(
    match: RawMatch,
    *,
    repo_root: Path,
    registry: Registry,
    run_id: str,
    today: date | None = None,
) -> Finding:
    today = today or datetime.now(UTC).date()
    canonical_id = canonicalize(match.matched_text)
    resolution: Resolution = resolve(canonical_id, registry)
    entry = resolution.entry if isinstance(resolution, Resolved) else None

    verdict = compute_verdict(resolution, today)
    severity = compute_severity(verdict, resolution, today)
    confidence = compute_confidence(resolution)

    relative_path = str(match.path.relative_to(repo_root))
    owner = find_owner(match.path, match.line, repo_root)
    content_hash = hashlib.sha256(match.path.read_bytes()).hexdigest()

    evidence = Evidence(
        source_uri=relative_path,
        locator=str(match.line),
        excerpt=match.matched_text,
        retrieved_at=datetime.now(UTC),
        content_hash=content_hash,
    )

    return Finding(
        identity=compute_identity(canonical_id, relative_path, match.symbol),
        product=ProductCode.EBB,
        rule_id=RULE_ID,
        subject=canonical_id,
        severity=severity,
        confidence=confidence,
        title=_title_for(canonical_id, verdict, entry),
        detail_md=_detail_md_for(canonical_id, entry),
        evidence=[evidence],
        owner=owner,
        deadline=entry.shutdown_at if entry else None,
        verdict=verdict,
        # No baseline mechanism exists for ebb's stateless local CLI yet — every finding from a
        # single `ebb scan` invocation is NEW. See FindingState's own docstring.
        state=FindingState.NEW,
        first_seen_run=run_id,
        rule_version=registry.version,
        engine_version=ENGINE_VERSION,
    )


def build_findings(
    repo_root: Path, registry: Registry, *, today: date | None = None
) -> list[Finding]:
    """The full pipeline, wired together for the first time: walk -> detect -> canonicalize ->
    resolve -> owner attribution -> verdict/severity/confidence -> Finding. One run_id shared
    across every finding from this invocation."""
    run_id = f"run-{uuid.uuid4()}"
    return [
        build_finding(match, repo_root=repo_root, registry=registry, run_id=run_id, today=today)
        for match in scan_repo(repo_root)
    ]
