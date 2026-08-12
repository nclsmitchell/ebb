import sys
from importlib import resources
from pathlib import Path

import typer
from rich.console import Console

from ebb.brand import BRAND
from ebb.build_findings import build_findings
from ebb.finding import Finding, Severity
from ebb.registry.loader import RegistryLoadError, load_registry
from ebb.render.annotations import render_annotations
from ebb.render.json_renderer import render_json
from ebb.render.markdown import render_markdown
from ebb.render.sarif import render_sarif
from ebb.render.terminal import render_terminal

_FORMATS = ("table", "markdown", "json", "sarif", "annotations")

app = typer.Typer(
    name="ebb", help=f"{BRAND} ebb — find model identifiers before a provider retires them."
)
console = Console()
error_console = Console(stderr=True)

_SEVERITY_ORDER = [
    Severity.INFO,
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
]


@app.callback()
def _callback() -> None:
    """Keeps `scan` addressable as `ebb scan PATH` — without a callback, Typer collapses an
    app with a single command into a bare `ebb PATH` invocation instead."""


def _default_registry_dir() -> Path:
    # Packaged as data inside the `ebb` distribution (src/ebb/registries/retirements/) so
    # `uvx foretop-ebb scan .` works on a cold machine with no monorepo checkout in sight
    # (specs/ebb.md §9's definition of done) — importlib.resources resolves relative to
    # wherever the installed package actually lives, whether that's an editable workspace
    # checkout or a normal site-packages install. --registry-dir still overrides this for
    # anyone pinning to their own fork of the data (specs/ebb.md §5: the registry becomes a
    # versioned dependency of its own eventually — this is the seam that day reuses).
    return Path(str(resources.files("ebb") / "registries" / "retirements"))


def _render(findings: list[Finding], fmt: str) -> str:
    if fmt == "table":
        return render_terminal(findings, no_color=not sys.stdout.isatty())
    if fmt == "markdown":
        return render_markdown(findings)
    if fmt == "json":
        return render_json(findings)
    if fmt == "sarif":
        import json

        return json.dumps(render_sarif(findings), indent=2, sort_keys=True)
    if fmt == "annotations":
        return render_annotations(findings)
    raise ValueError(f"unknown format: {fmt!r}")


@app.command()
def scan(
    path: Path = typer.Argument(Path("."), help="Repository path to scan."),  # noqa: B008
    fmt: str = typer.Option(
        "table", "--format", help="Output format: table, markdown, json, sarif, or annotations."
    ),
    registry_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--registry-dir",
        help="Directory of registry YAML files. Defaults to this repo's registries/retirements/.",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        help="Exit 1 if any finding's severity is at or above this level "
        "(info, low, medium, high, critical). Unset: always exit 0.",
    ),
) -> None:
    """Scan a repository for model references and report their retirement status.

    Exit codes are an API (specs/ebb.md §6): 0 clean or below --fail-on's threshold, 1 a
    finding met or exceeded --fail-on, 2 an internal error (bad --format, registry failed to
    load). These must never be conflated.
    """
    if fmt not in _FORMATS:
        error_console.print(f"Unknown --format {fmt!r}. Choose one of: {', '.join(_FORMATS)}.")
        raise typer.Exit(code=2)

    threshold: Severity | None = None
    if fail_on is not None:
        try:
            threshold = Severity(fail_on)
        except ValueError:
            error_console.print(
                f"Unknown --fail-on {fail_on!r}. Choose one of: "
                f"{', '.join(s.value for s in _SEVERITY_ORDER)}."
            )
            raise typer.Exit(code=2) from None

    registry_paths = sorted((registry_dir or _default_registry_dir()).glob("*.yaml"))
    try:
        registry = load_registry(registry_paths)
    except RegistryLoadError as exc:
        error_console.print(f"Registry failed to load: {exc}")
        raise typer.Exit(code=2) from exc

    findings = build_findings(path.resolve(), registry)
    print(_render(findings, fmt))

    if threshold is not None:
        threshold_rank = _SEVERITY_ORDER.index(threshold)
        if any(_SEVERITY_ORDER.index(f.severity) >= threshold_rank for f in findings):
            raise typer.Exit(code=1)
