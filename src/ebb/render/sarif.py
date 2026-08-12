from ebb import __version__ as ENGINE_VERSION  # noqa: N812
from ebb.finding import Finding, Severity

SCHEMA_URI = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)

# SARIF 2.1.0 has 4 result levels (none/note/warning/error); Finding has 5 severities. Verified
# against the real schema (definitions.result.properties.level.enum), not written from memory.
_SEVERITY_TO_SARIF_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "warning",
    Severity.INFO: "note",
}


def render_sarif(findings: list[Finding]) -> dict[str, object]:
    """Returns the SARIF log as a dict, not a JSON string — tests validate the structure
    directly against the real fetched schema (jsonschema.validate), and a dict is what that
    needs. Serialize with json.dumps at the call site for file/stdout output."""
    rule_ids = sorted({f.rule_id for f in findings})
    rules = [{"id": rule_id, "name": rule_id} for rule_id in rule_ids]

    results: list[dict[str, object]] = []
    for finding in findings:
        locations = []
        for evidence in finding.evidence:
            physical_location: dict[str, object] = {
                "artifactLocation": {"uri": evidence.source_uri}
            }
            if evidence.locator is not None and evidence.locator.isdigit():
                physical_location["region"] = {"startLine": int(evidence.locator)}
            locations.append({"physicalLocation": physical_location})

        results.append(
            {
                "ruleId": finding.rule_id,
                "level": _SEVERITY_TO_SARIF_LEVEL[finding.severity],
                "message": {"text": finding.title},
                "locations": locations,
                "properties": {
                    "subject": finding.subject,
                    "verdict": finding.verdict.value,
                    "confidence": finding.confidence.value,
                    "owner": finding.owner,
                    "deadline": finding.deadline.isoformat() if finding.deadline else None,
                },
            }
        )

    return {
        "$schema": SCHEMA_URI,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ebb",
                        "version": ENGINE_VERSION,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
