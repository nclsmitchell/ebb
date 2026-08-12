from datetime import date

from ebb.finding import Confidence, Severity, Verdict
from ebb.registry.resolve import Resolution, Resolved


def compute_verdict(resolution: Resolution, today: date) -> Verdict:
    """SUITE_ARCHITECTURE.md §3: unknown is a first-class verdict, never clear, for anything
    resolve() couldn't verify. For a verified entry: no shutdown date on record is CLEAR
    (actively supported), a shutdown date already passed is BREAK (code referencing it is
    failing now, not eventually), and a future shutdown date is DRIFT (scheduled, not yet
    broken — the warning state this whole product exists to surface in time)."""
    if not isinstance(resolution, Resolved):
        return Verdict.UNKNOWN
    shutdown_at = resolution.entry.shutdown_at
    if shutdown_at is None:
        return Verdict.CLEAR
    return Verdict.BREAK if shutdown_at <= today else Verdict.DRIFT


def compute_severity(verdict: Verdict, resolution: Resolution, today: date) -> Severity:
    """BREAK is always CRITICAL — it's failing now. DRIFT scales with days remaining: the
    plan's own domain language ('days-to-deadline', specs/ebb.md §2.2) is exactly this. UNKNOWN
    is LOW, not INFO: worth a human look, but ebb has no basis to claim it's dangerous when it
    hasn't verified the model's status at all."""
    if verdict is Verdict.BREAK:
        return Severity.CRITICAL
    if verdict is Verdict.CLEAR:
        return Severity.INFO
    if verdict is Verdict.UNKNOWN:
        return Severity.LOW

    assert isinstance(resolution, Resolved)
    assert resolution.entry.shutdown_at is not None
    days_remaining = (resolution.entry.shutdown_at - today).days
    if days_remaining <= 30:
        return Severity.HIGH
    if days_remaining <= 90:
        return Severity.MEDIUM
    return Severity.LOW


def compute_confidence(resolution: Resolution) -> Confidence:
    """CERTAIN when resolve() found a verified registry entry; PROBABLE when the text merely
    looks model-id-shaped per detect/patterns.py but isn't a curated, verified entry. Neither
    is AMBIGUOUS — that confidence level is reserved for LLM-assisted classification of
    unknown-but-model-shaped strings (specs/ebb.md DEC-03), which doesn't exist yet."""
    return Confidence.CERTAIN if isinstance(resolution, Resolved) else Confidence.PROBABLE
