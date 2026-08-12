from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ebb.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingState,
    ProductCode,
    Severity,
    Verdict,
)


def make_evidence(**overrides: object) -> Evidence:
    defaults: dict[str, object] = {
        "source_uri": "src/app.py",
        "locator": "3",
        "excerpt": 'PRIMARY_MODEL = "gpt-4-turbo-2024-04-09"',
        "retrieved_at": datetime(2026, 8, 12, tzinfo=UTC),
        "content_hash": "abc123",
    }
    defaults.update(overrides)
    return Evidence(**defaults)  # type: ignore[arg-type]


def make_finding(**overrides: object) -> Finding:
    defaults: dict[str, object] = {
        "identity": "deadbeef",
        "product": ProductCode.EBB,
        "rule_id": "ebb.retirement",
        "subject": "gpt-4-turbo-2024-04-09",
        "severity": Severity.HIGH,
        "confidence": Confidence.CERTAIN,
        "title": "gpt-4-turbo-2024-04-09 retires 2026-10-23",
        "detail_md": "details",
        "evidence": [make_evidence()],
        "owner": "@ebb-team",
        "deadline": None,
        "verdict": Verdict.DRIFT,
        "state": FindingState.NEW,
        "first_seen_run": "run-1",
        "rule_version": "registryversion123",
        "engine_version": "0.1.0",
    }
    defaults.update(overrides)
    return Finding(**defaults)  # type: ignore[arg-type]


def test_a_complete_finding_is_valid() -> None:
    finding = make_finding()
    assert finding.verdict is Verdict.DRIFT
    assert len(finding.evidence) == 1


def test_evidence_must_never_be_empty() -> None:
    with pytest.raises(ValidationError, match="evidence must never be empty"):
        make_finding(evidence=[])


def test_unknown_is_a_first_class_verdict_not_a_default() -> None:
    finding = make_finding(verdict=Verdict.UNKNOWN, confidence=Confidence.PROBABLE)
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.verdict != Verdict.CLEAR


def test_evidence_source_uri_must_not_be_blank() -> None:
    with pytest.raises(ValidationError):
        make_evidence(source_uri="   ")


def test_finding_and_state_are_independent_axes() -> None:
    """SUITE_ARCHITECTURE.md §3: 'a finding can be unknown and persisting at the same time.'"""
    finding = make_finding(verdict=Verdict.UNKNOWN, state=FindingState.PERSISTING)
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.state is FindingState.PERSISTING


def test_finding_is_frozen() -> None:
    finding = make_finding()
    with pytest.raises(ValidationError):
        finding.verdict = Verdict.CLEAR  # type: ignore[misc]
