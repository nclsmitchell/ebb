from datetime import date

import pytest

from ebb.finding import Confidence, Severity, Verdict
from ebb.registry.models import RegistryEntry
from ebb.registry.resolve import Resolved, Unknown
from ebb.verdict import compute_confidence, compute_severity, compute_verdict

TODAY = date(2026, 8, 12)


def make_entry(**overrides: object) -> RegistryEntry:
    defaults: dict[str, object] = {
        "canonical_id": "gpt-4-turbo",
        "provider": "openai",
        "source_url": "https://developers.openai.com/api/docs/deprecations",
        "verified_at": TODAY,
    }
    defaults.update(overrides)
    return RegistryEntry(**defaults)  # type: ignore[arg-type]


def test_unresolved_is_unknown() -> None:
    assert compute_verdict(Unknown(raw_text="whatever"), TODAY) is Verdict.UNKNOWN


def test_resolved_with_no_shutdown_date_is_clear() -> None:
    resolution = Resolved(entry=make_entry(shutdown_at=None), matched_via="canonical_id")
    assert compute_verdict(resolution, TODAY) is Verdict.CLEAR


def test_resolved_with_a_past_shutdown_date_is_break() -> None:
    entry = make_entry(shutdown_at=date(2026, 1, 1))
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_verdict(resolution, TODAY) is Verdict.BREAK


def test_resolved_with_shutdown_date_today_is_break() -> None:
    """The deadline itself is the failure boundary, not the day after it."""
    entry = make_entry(shutdown_at=TODAY)
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_verdict(resolution, TODAY) is Verdict.BREAK


def test_resolved_with_a_future_shutdown_date_is_drift() -> None:
    entry = make_entry(shutdown_at=date(2026, 12, 1))
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_verdict(resolution, TODAY) is Verdict.DRIFT


def test_break_is_always_critical() -> None:
    entry = make_entry(shutdown_at=date(2020, 1, 1))
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_severity(Verdict.BREAK, resolution, TODAY) is Severity.CRITICAL


def test_clear_is_info() -> None:
    entry = make_entry(shutdown_at=None)
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_severity(Verdict.CLEAR, resolution, TODAY) is Severity.INFO


def test_unknown_is_low_not_info() -> None:
    assert compute_severity(Verdict.UNKNOWN, Unknown(raw_text="x"), TODAY) is Severity.LOW


@pytest.mark.parametrize(
    ("days_remaining", "expected"),
    [
        (1, Severity.HIGH),
        (30, Severity.HIGH),
        (31, Severity.MEDIUM),
        (90, Severity.MEDIUM),
        (91, Severity.LOW),
        (365, Severity.LOW),
    ],
)
def test_drift_severity_scales_with_days_remaining(days_remaining: int, expected: Severity) -> None:
    from datetime import timedelta

    entry = make_entry(shutdown_at=TODAY + timedelta(days=days_remaining))
    resolution = Resolved(entry=entry, matched_via="canonical_id")
    assert compute_severity(Verdict.DRIFT, resolution, TODAY) is expected


def test_confidence_is_certain_when_resolved() -> None:
    resolution = Resolved(entry=make_entry(), matched_via="canonical_id")
    assert compute_confidence(resolution) is Confidence.CERTAIN


def test_confidence_is_probable_when_unknown() -> None:
    assert compute_confidence(Unknown(raw_text="x")) is Confidence.PROBABLE
