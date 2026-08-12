from io import StringIO

from rich.console import Console
from rich.table import Table

from ebb.finding import Finding


def render_terminal(findings: list[Finding], *, no_color: bool = False) -> str:
    """`no_color` matters beyond tests: the caller (the CLI) has already decided whether the
    real destination is a terminal via `sys.stdout.isatty()` and passes that decision down.
    This function renders into an internal StringIO buffer, which is never itself a tty, so
    Rich's own terminal autodetection can't be trusted here — `force_terminal=not no_color`
    makes rendering depend only on the explicit `no_color` argument, not on ambient environment
    variables Rich also consults (e.g. FORCE_COLOR), which made this non-deterministic across
    machines: a local shell with such a variable set produced colored output by accident while
    CI, with no tty and no such variable, silently produced plain output either way."""
    table = Table(title="ebb scan")
    table.add_column("Severity")
    table.add_column("Verdict")
    table.add_column("Subject")
    table.add_column("File")
    table.add_column("Line", justify="right")
    table.add_column("Owner")
    table.add_column("Deadline")

    for finding in findings:
        evidence = finding.evidence[0]
        table.add_row(
            finding.severity.value,
            finding.verdict.value,
            finding.subject,
            evidence.source_uri,
            evidence.locator or "",
            finding.owner or "—",
            finding.deadline.isoformat() if finding.deadline else "—",
        )

    buffer = StringIO()
    console = Console(
        file=buffer,
        width=120,
        no_color=no_color,
        highlight=not no_color,
        force_terminal=not no_color,
    )
    console.print(table)
    console.print(f"{len(findings)} finding(s)")
    return buffer.getvalue()
