from datetime import UTC, date, datetime

from ebb.finding import Confidence, Evidence, Finding, FindingState, ProductCode, Severity, Verdict
from ebb.render.annotations import render_annotations


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


def test_high_severity_renders_as_an_error_annotation() -> None:
    output = render_annotations([make_finding(severity=Severity.HIGH)])
    assert output.startswith("::error file=src/app.py,line=3,title=ebb%3A gpt-4-turbo (drift)::")


def test_critical_severity_is_also_an_error() -> None:
    output = render_annotations([make_finding(severity=Severity.CRITICAL)])
    assert output.startswith("::error ")


def test_medium_and_low_severity_render_as_warning() -> None:
    assert render_annotations([make_finding(severity=Severity.MEDIUM)]).startswith("::warning ")
    assert render_annotations([make_finding(severity=Severity.LOW)]).startswith("::warning ")


def test_info_severity_renders_as_notice() -> None:
    output = render_annotations([make_finding(severity=Severity.INFO)])
    assert output.startswith("::notice ")


def test_message_includes_title_deadline_and_owner() -> None:
    output = render_annotations([make_finding()])
    message = output.split("::")[-1]
    assert "gpt-4-turbo retires 2026-10-23" in message
    assert "Deadline: 2026-10-23" in message
    assert "Owner: @ebb-team" in message


def test_missing_owner_and_deadline_are_omitted_not_blank() -> None:
    output = render_annotations([make_finding(owner=None, deadline=None)])
    message = output.split("::")[-1]
    assert "Deadline:" not in message
    assert "Owner:" not in message


def test_missing_line_number_defaults_to_1() -> None:
    finding = make_finding(
        evidence=[
            Evidence(
                source_uri="src/app.py",
                locator=None,
                excerpt="gpt-4-turbo",
                retrieved_at=datetime(2026, 8, 12, tzinfo=UTC),
                content_hash="abc123",
            )
        ]
    )
    output = render_annotations([finding])
    assert ",line=1," in output


def test_comma_and_colon_in_file_path_are_percent_encoded_in_properties() -> None:
    finding = make_finding(
        evidence=[
            Evidence(
                source_uri="weird,path:name.py",
                locator="1",
                excerpt="gpt-4-turbo",
                retrieved_at=datetime(2026, 8, 12, tzinfo=UTC),
                content_hash="abc123",
            )
        ]
    )
    output = render_annotations([finding])
    assert "file=weird%2Cpath%3Aname.py," in output


def test_empty_findings_render_nothing() -> None:
    assert render_annotations([]) == ""


def test_two_findings_render_two_lines() -> None:
    output = render_annotations([make_finding(), make_finding(subject="claude-3-haiku")])
    lines = output.splitlines()
    assert len(lines) == 2
