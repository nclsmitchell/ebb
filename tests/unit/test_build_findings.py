from datetime import date
from pathlib import Path

from ebb import __version__ as ENGINE_VERSION  # noqa: N812
from ebb.build_findings import build_findings
from ebb.finding import Confidence, Severity, Verdict
from ebb.registry.loader import Registry
from ebb.registry.models import RegistryEntry

TODAY = date(2026, 8, 12)


def make_registry(*entries: RegistryEntry) -> Registry:
    return Registry(entries=entries, version="test-registry-version")


def make_entry(**overrides: object) -> RegistryEntry:
    defaults: dict[str, object] = {
        "canonical_id": "gpt-4-turbo",
        "provider": "openai",
        "source_url": "https://developers.openai.com/api/docs/deprecations",
        "verified_at": TODAY,
    }
    defaults.update(overrides)
    return RegistryEntry(**defaults)  # type: ignore[arg-type]


def test_a_retired_model_produces_a_break_finding(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('MODEL = "gpt-4-turbo"\n')
    registry = make_registry(
        make_entry(
            canonical_id="gpt-4-turbo",
            shutdown_at=date(2026, 1, 1),
            replacement_id="gpt-5.6-sol",
        )
    )

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.subject == "gpt-4-turbo"
    assert finding.verdict is Verdict.BREAK
    assert finding.severity is Severity.CRITICAL
    assert finding.confidence is Confidence.CERTAIN
    assert finding.deadline == date(2026, 1, 1)
    assert "gpt-5.6-sol" in finding.detail_md
    assert finding.rule_version == "test-registry-version"
    assert finding.engine_version == ENGINE_VERSION
    assert len(finding.identity) == 16
    assert len(finding.evidence) == 1
    assert finding.evidence[0].source_uri == "app.py"
    assert finding.evidence[0].locator == "1"
    assert finding.evidence[0].excerpt == "gpt-4-turbo"


def test_an_actively_supported_model_produces_a_clear_finding(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('MODEL = "gpt-4-turbo"\n')
    registry = make_registry(make_entry(canonical_id="gpt-4-turbo", shutdown_at=None))

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len(findings) == 1
    assert findings[0].verdict is Verdict.CLEAR
    assert findings[0].severity is Severity.INFO
    assert findings[0].deadline is None


def test_an_unregistered_model_produces_an_unknown_finding_not_clear(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('MODEL = "gpt-4-turbo"\n')
    registry = make_registry()  # empty — nothing verified

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len(findings) == 1
    assert findings[0].verdict is Verdict.UNKNOWN
    assert findings[0].verdict is not Verdict.CLEAR
    assert findings[0].confidence is Confidence.PROBABLE


def test_a_bedrock_wrapped_reference_still_resolves_via_canonicalize_then_resolve(
    tmp_path: Path,
) -> None:
    (tmp_path / "app.py").write_text('MODEL = "us.anthropic.claude-3-haiku-20240307-v1:0"\n')
    registry = make_registry(
        make_entry(
            canonical_id="claude-3-haiku-20240307",
            provider="anthropic",
            shutdown_at=date(2026, 4, 20),
        )
    )

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len(findings) == 1
    assert findings[0].subject == "claude-3-haiku-20240307"
    assert findings[0].verdict is Verdict.BREAK


def test_two_references_in_different_files_produce_two_independent_findings(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text('MODEL = "gpt-4-turbo"\n')
    (tmp_path / "b.py").write_text('MODEL = "gpt-4-turbo"\n')
    registry = make_registry(make_entry(canonical_id="gpt-4-turbo", shutdown_at=None))

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len(findings) == 2
    assert findings[0].identity != findings[1].identity
    assert {f.evidence[0].source_uri for f in findings} == {"a.py", "b.py"}


def test_no_references_produces_no_findings(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n")
    assert build_findings(tmp_path, make_registry(), today=TODAY) == []


def test_every_finding_shares_one_run_id(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('MODEL = "gpt-4-turbo"\n')
    (tmp_path / "b.py").write_text('MODEL = "gpt-4-turbo"\n')
    registry = make_registry(make_entry(canonical_id="gpt-4-turbo", shutdown_at=None))

    findings = build_findings(tmp_path, registry, today=TODAY)

    assert len({f.first_seen_run for f in findings}) == 1
