import json
from datetime import UTC, date, datetime
from pathlib import Path

import jsonschema
import pytest

from ebb.finding import Confidence, Evidence, Finding, FindingState, ProductCode, Severity, Verdict
from ebb.render.sarif import render_sarif

SCHEMA_PATH = Path(__file__).parent.parent / "fixtures" / "sarif-schema-2.1.0.json"


@pytest.fixture(scope="module")
def sarif_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text())


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


def test_output_validates_against_the_real_sarif_schema(sarif_schema: dict[str, object]) -> None:
    log = render_sarif([make_finding()])
    jsonschema.validate(instance=log, schema=sarif_schema)


def test_empty_findings_still_validates(sarif_schema: dict[str, object]) -> None:
    log = render_sarif([])
    jsonschema.validate(instance=log, schema=sarif_schema)
    assert log["runs"][0]["results"] == []  # type: ignore[index]


def test_severity_maps_to_a_valid_sarif_level(sarif_schema: dict[str, object]) -> None:
    findings = [make_finding(severity=s) for s in Severity]
    log = render_sarif(findings)
    jsonschema.validate(instance=log, schema=sarif_schema)
    levels = {r["level"] for r in log["runs"][0]["results"]}  # type: ignore[index]
    assert levels <= {"none", "note", "warning", "error"}


def test_line_locator_becomes_a_sarif_region() -> None:
    log = render_sarif([make_finding()])
    location = log["runs"][0]["results"][0]["locations"][0]  # type: ignore[index]
    assert location["physicalLocation"]["artifactLocation"]["uri"] == "src/app.py"
    assert location["physicalLocation"]["region"]["startLine"] == 3


def test_result_carries_findable_metadata_in_properties() -> None:
    log = render_sarif([make_finding()])
    props = log["runs"][0]["results"][0]["properties"]  # type: ignore[index]
    assert props["subject"] == "gpt-4-turbo"
    assert props["verdict"] == "drift"
    assert props["owner"] == "@ebb-team"


def test_output_is_json_serializable() -> None:
    log = render_sarif([make_finding()])
    json.dumps(log)  # must not raise
