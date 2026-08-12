from datetime import UTC, date, datetime

from ebb.finding import Confidence, Evidence, Finding, FindingState, ProductCode, Severity, Verdict
from ebb.render.markdown import render_markdown


def make_finding(**overrides: object) -> Finding:
    defaults: dict[str, object] = {
        "identity": "deadbeef",
        "product": ProductCode.EBB,
        "rule_id": "ebb.retirement",
        "subject": "gpt-4-turbo",
        "severity": Severity.HIGH,
        "confidence": Confidence.CERTAIN,
        "title": "gpt-4-turbo retires 2026-10-23",
        "detail_md": "details",
        "evidence": [
            Evidence(
                source_uri="src/app.py",
                locator="3",
                excerpt="gpt-4-turbo",
                retrieved_at=datetime(2026, 8, 12, tzinfo=UTC),
                content_hash="abc123",
            )
        ],
        "owner": "@ebb-team",
        "deadline": date(2026, 10, 23),
        "verdict": Verdict.DRIFT,
        "state": FindingState.NEW,
        "first_seen_run": "run-1",
        "rule_version": "regv1",
        "engine_version": "0.1.0",
    }
    defaults.update(overrides)
    return Finding(**defaults)  # type: ignore[arg-type]


def test_renders_a_markdown_table_row_per_finding() -> None:
    output = render_markdown([make_finding()])
    assert "| high | drift | `gpt-4-turbo` | src/app.py:3 | @ebb-team | 2026-10-23 |" in output
    assert "**1 finding(s)**" in output


def test_empty_findings_render_a_clean_message_not_an_empty_table() -> None:
    output = render_markdown([])
    assert output == "No model references found.\n"


def test_missing_owner_and_deadline_render_as_em_dash() -> None:
    output = render_markdown([make_finding(owner=None, deadline=None)])
    assert "| — | — |" in output
