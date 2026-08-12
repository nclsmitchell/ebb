import json
from datetime import UTC, date, datetime

from ebb.finding import Confidence, Evidence, Finding, FindingState, ProductCode, Severity, Verdict
from ebb.render.json_renderer import render_json


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


def test_renders_valid_json_round_tripping_every_field() -> None:
    output = render_json([make_finding()])
    parsed = json.loads(output)

    assert len(parsed) == 1
    entry = parsed[0]
    assert entry["subject"] == "gpt-4-turbo"
    assert entry["severity"] == "high"
    assert entry["verdict"] == "drift"
    assert entry["deadline"] == "2026-10-23"
    assert entry["evidence"][0]["source_uri"] == "src/app.py"


def test_empty_findings_render_an_empty_json_array() -> None:
    assert json.loads(render_json([])) == []
