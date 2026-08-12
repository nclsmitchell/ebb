from ebb.finding import Finding


def render_markdown(findings: list[Finding]) -> str:
    """For PR comments (specs/ebb.md §2.5). The upsert-by-marker logic that avoids posting a
    second comment on every push is Session 8's job (GitHub Action wiring) — this only
    produces the content."""
    if not findings:
        return "No model references found.\n"

    lines = [
        "| Severity | Verdict | Subject | File | Owner | Deadline |",
        "|---|---|---|---|---|---|",
    ]
    for finding in findings:
        evidence = finding.evidence[0]
        location = evidence.source_uri
        if evidence.locator:
            location += f":{evidence.locator}"
        deadline = finding.deadline.isoformat() if finding.deadline else "—"
        owner = finding.owner or "—"
        lines.append(
            f"| {finding.severity.value} | {finding.verdict.value} | `{finding.subject}` "
            f"| {location} | {owner} | {deadline} |"
        )

    lines.append(f"\n**{len(findings)} finding(s)**")
    return "\n".join(lines) + "\n"
