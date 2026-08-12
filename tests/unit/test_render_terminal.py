from datetime import UTC, date, datetime

from ebb.finding import Confidence, Evidence, Finding, FindingState, ProductCode, Severity, Verdict
from ebb.render.terminal import render_terminal


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


def test_renders_every_finding_field() -> None:
    output = render_terminal([make_finding()], no_color=True)
    assert "gpt-4-turbo" in output
    assert "high" in output
    assert "drift" in output
    assert "src/app.py" in output
    assert "@ebb-team" in output
    assert "2026-10-23" in output
    assert "1 finding(s)" in output


def test_renders_empty_findings_without_crashing() -> None:
    output = render_terminal([], no_color=True)
    assert "0 finding(s)" in output


def test_missing_owner_and_deadline_render_as_em_dash() -> None:
    output = render_terminal([make_finding(owner=None, deadline=None)], no_color=True)
    assert "—" in output


def test_default_is_color_capable_not_forced_plain() -> None:
    """The CLI wants real color on an actual terminal — no_color defaults to False. This is
    what originally broke plain substring assertions: Rich's highlighter wraps things that look
    like numbers (e.g. the finding count) in color codes, splitting "1 finding(s)" apart even
    though the destination (a StringIO) isn't a terminal. no_color=True disables that
    highlighting; it doesn't promise zero ANSI whatsoever (bold/italic table styling is a
    separate concern from color and survives either way)."""
    colored = render_terminal([make_finding()])
    plain = render_terminal([make_finding()], no_color=True)
    assert colored != plain
    assert "1 finding(s)" not in colored  # split apart by color codes around "1"
    assert "1 finding(s)" in plain
