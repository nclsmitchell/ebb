from ebb.finding import Finding, Severity

# GitHub workflow-command level per severity. error/warning/notice are the three levels GitHub
# Actions supports (docs.github.com/en/actions/using-workflows/workflow-commands-for-github-
# actions) — verified, not guessed, same discipline as the SARIF level mapping in render/sarif.py.
_ANNOTATION_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "warning",
    Severity.INFO: "notice",
}


def _escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    # Same as _escape_data, plus : and , — those are structurally significant in the
    # `key=value,key=value` property list, so they need encoding there but not in the message
    # body. Matches @actions/core's escapeData/escapeProperty exactly (verified against
    # actions/toolkit's own source), not a guess at the format.
    return _escape_data(text).replace(":", "%3A").replace(",", "%2C")


def render_annotations(findings: list[Finding]) -> str:
    """GitHub workflow-command syntax (`::error file=...,line=...::message`), printed to a
    step's stdout. GitHub turns these into inline PR annotations on the Files Changed tab with
    zero extra permissions and no separate API call — unlike SARIF upload, which needs
    `security-events: write`. That makes this the zero-friction default for the composite
    Action; SARIF (render/sarif.py) is still available for anyone who wants Code Scanning's
    persistent history instead."""
    lines = []
    for finding in findings:
        evidence = finding.evidence[0]
        level = _ANNOTATION_LEVEL[finding.severity]
        line = evidence.locator if evidence.locator and evidence.locator.isdigit() else "1"
        title = _escape_property(f"ebb: {finding.subject} ({finding.verdict.value})")
        file_prop = _escape_property(evidence.source_uri)

        message_parts = [finding.title]
        if finding.deadline:
            message_parts.append(f"Deadline: {finding.deadline.isoformat()}")
        if finding.owner:
            message_parts.append(f"Owner: {finding.owner}")
        message = _escape_data("\n".join(message_parts))

        lines.append(f"::{level} file={file_prop},line={line},title={title}::{message}")
    return "\n".join(lines) + ("\n" if lines else "")
