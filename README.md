# ebb

> Tells an engineering team which repos, jobs, prompts and owners break when an AI provider
> retires a model — before the deadline becomes an outage.

A provider announces a retirement date. Somewhere in your repos, Airflow DAGs, Terraform
variables and prompt templates there's a hardcoded model string nobody remembers. `ebb` finds
every one of them, joins it to the provider's real retirement date, and tells you who owns it.

## Install and run

```
uvx foretop-ebb scan .
```

No config, no account, no network call beyond installing the package — detection is entirely
local and deterministic, matched against a versioned registry bundled in the package. Add
`--format sarif` for GitHub Code Scanning, `--format markdown` for a PR comment, or
`--fail-on critical` to make CI fail when something's actually urgent (see below for exit
codes). `ebb scan --help` lists everything.

## Use it as a GitHub Action

```yaml
- uses: nclsmitchell/ebb@main
  with:
    fail-on: critical # info | low | medium | high | critical; empty string = report-only
```

Annotates the pull request inline and upserts one summary comment (finds its own previous
comment by an HTML marker and edits it — never posts a second one on repeat pushes). Needs
`permissions: pull-requests: write` in the calling workflow.

## License

Apache-2.0. This file tracks build status below; the source-of-truth product spec lives in the
private monorepo this is mirrored from (see `scripts/sync-ebb-mirror.sh` there).

## Status

**Slice 1** (Session 3): a Typer CLI that walks a repository and detects model-identifier-shaped
strings in Python, TypeScript, YAML, TOML, JSON, Terraform, Dockerfiles and Jupyter notebooks.
Deterministic pattern matching only.

```
uv run --package foretop-ebb ebb scan <path>
```

Detectors are pure functions `(path, content) -> list[RawMatch]`, registered in a table in
`src/ebb/detect/registry.py`. Adding a language means one new detector file plus one new fixture
under `tests/fixtures/` — nothing else changes.

**Registry (Session 4):** `src/ebb/registry/` loads `src/ebb/registries/retirements/*.yaml` —
real retirement data for OpenAI, Anthropic and Google, sourced from each provider's live
deprecations
page, never invented. `RegistryEntry` requires `source_url` and `verified_at`; a record missing
either fails the whole load (`RegistryLoadError`) rather than silently dropping it. Loading warns
(`StaleRegistryEntryWarning`) on any entry verified more than 90 days ago. `resolve(raw_text,
registry)` is an exact-match lookup against `canonical_id` and curated `aliases` only — no
prefix or fuzzy matching, so an uncurated floating alias (`claude-3-opus-latest`) resolves to
`Unknown`, never to whatever entry happens to share a prefix. `registry.version` is a
content-derived hash, stamped onto every `Finding.rule_version` (Session 6).

**Canonicalisation (Session 5):** `src/ebb/canonicalize.py` — pure, isolated, no registry lookup,
no I/O. Collapses AWS Bedrock cross-Region inference profile IDs and vendor-prefixed model IDs
(`us.anthropic.claude-3-haiku-20240307-v1:0` — the literal example from AWS's own docs) and GCP
Vertex AI publisher-model resource paths (`publishers/{vendor}/models/{id}`, optionally
`projects/.../locations/...`-prefixed) plus their respective `-v{N}:{M}` / `@{N}` version
suffixes, down to the bare dated-snapshot id a provider's own API would use directly. Property-
tested with Hypothesis for idempotency and round-tripping, per the plan's explicit requirement.
Deliberately does **not** strip `-latest` / `-preview` suffixes — some of those are curated as
their own whole registry entries (`chatgpt-4o-latest`), and stripping would silently break their
resolution; an uncurated floating alias stays exactly as unresolvable after canonicalisation as
before, which is correct (see Session 4's `resolve()` tests).

**Owner attribution (Session 5):** `src/ebb/owner.py` — CODEOWNERS first (reusing `pathspec`'s
gitignore matching, since GitHub documents CODEOWNERS pattern syntax as the same rules; last
matching rule in the file wins, per GitHub's own precedence), `git blame` on the specific line as
fallback. Returns `None` rather than raising when neither source has an answer — a file with no
declared owner and no git history is a legitimate, common outcome.

**Findings, verdicts and renderers (Session 6):** the whole pipeline is wired together for the
first time — `src/ebb/build_findings.py` runs walk → detect → `canonicalize()` → `resolve()` →
`find_owner()` → verdict/severity/confidence (`src/ebb/verdict.py`) → a `Finding`
(`src/ebb/finding.py`, the SUITE_ARCHITECTURE.md §3 model: `evidence` can never be empty,
enforced by a Pydantic validator, and `unknown` is a first-class `Verdict`, not a fallback).
Identity is `sha256(canonical_id | file_path | symbol)[:16]` — deliberately excludes the line
number; `symbol` is a lightweight, language-agnostic "nearest assignment target" heuristic
(`detect/scan_text.nearest_symbol`), not full per-language AST scoping, which was out of scope
for this session.

Verdict logic: `unknown` for anything `resolve()` couldn't verify; for a verified entry, no
shutdown date on record is `clear`, a shutdown date already passed is `break` (critical severity
— it's failing now, not eventually), a future one is `drift` (severity scales with days
remaining: ≤30d high, ≤90d medium, else low).

```
uv run --package foretop-ebb ebb scan <path> [--format table|markdown|json|sarif] [--fail-on SEVERITY]
```

Four renderers (`src/ebb/render/`): terminal (Rich, colour-capable — `--format table`, the
default), Markdown (for PR comments), JSON, and SARIF 2.1.0. The SARIF renderer is validated in
tests against the real schema fetched from OASIS's own repo (committed at
`tests/fixtures/sarif-schema-2.1.0.json`), not written from memory. `--fail-on SEVERITY` makes
exit code 1 when any finding meets or exceeds that severity; exit codes are an API (specs/ebb.md
§6) — 0 clean, 1 threshold met, 2 internal error (bad `--format`/`--fail-on`, registry failed to
load) — and these are never conflated.

`--registry-dir` overrides where registry YAML is loaded from; the default is the copy bundled
inside the `foretop-ebb` distribution itself (`src/ebb/registries/retirements/`, resolved via
`importlib.resources` — see Session 8 below), so it works identically whether ebb is running
from an editable monorepo checkout or a `pip`/`uvx`-installed wheel.

Known gap (detection is not the issue — Session 7's golden corpus scores every detector at
1.000 precision/recall): `canonicalize()` only strips AWS Bedrock and GCP Vertex AI wrapper
syntax, not a generic OpenAI-style dated-snapshot suffix. `gpt-4-turbo-2024-04-09` is detected
correctly as a whole match, but `canonicalize()` passes it through unchanged, and the registry
has no `gpt-4-turbo-2024-04-09` entry or alias — only bare `gpt-4-turbo` — so it resolves
`unknown` instead of joining to the real tracked entry. Not fixed here deliberately: generic
snapshot-suffix stripping has the same failure mode `canonicalize()` already refuses for
`-latest`/`-preview` (some dated suffixes are themselves curated as distinct whole entries,
and blind-stripping would break their resolution) — it needs the same care as that decision,
not a quick patch bolted onto Session 8's actual scope.

`packages/keel` does not exist yet and ebb does not depend on it — see SUITE_ARCHITECTURE.md §8.
Shared code is extracted in Session 10, against ebb and telltale together, not guessed at now.

**The accuracy floor (Session 7):** `tests/golden/` holds 30 hand-labelled repository fixtures,
3–5 per detector, covering all 8 detectors (`python`, `typescript`, `yaml`, `json`, `toml`,
`terraform`, `dockerfile`, `notebook`). Ground truth lives in `tests/golden_manifest.yaml` — kept
*outside* `tests/golden/` on purpose: a ground-truth file with model-id strings in it living
*inside* the scanned tree would itself get scanned and picked up as a spurious match. Labels
reflect real, current OpenAI/Anthropic/Google model-id shapes, not what the detector already
happened to catch — the entire point is that a gap between the two is a real bug, not a fixture
mistake.

`tests/unit/test_golden_corpus.py` (`make accuracy` to run it directly) scores every detector
**independently** — precision and recall are never pooled into one aggregate, because an average
across 8 detectors can hide one that's badly broken. The floor is precision ≥ 0.95 and recall ≥
0.85 per detector; a second test asserts every detector has at least one pure-decoy fixture (zero
expected matches), so a detector that's simply never tempted can't pass on a technicality.

First run against the corpus failed 6 of 8 detectors on real gaps: `patterns.py` had no o3/o4
family at all (only `o1`), no `gpt-5` family, and `gpt-4.1` silently matched as the shorter,
wrong `gpt-4` (alternation tries branches in order — with bare `4` before `4\.\d+`, "gpt-4.1"
matched only "gpt-4" and quietly dropped the `.1` that makes it a different model). Fixed in
`patterns.py` by adding the missing families and reordering the OpenAI alternation so the
longer, more specific branch is tried first — not by loosening the 0.95/0.85 floor, which never
moved. Also extended the OpenAI and Gemini date/qualifier suffixes to cover the bare-4-digit
snapshot convention (`gpt-4-0125-preview`) and `-preview`/`-exp` qualifiers
(`gemini-3-pro-preview`), both real, both previously truncating to a shorter, wrong match rather
than the full one. All 8 detectors now score 1.000 precision / 1.000 recall against the corpus.
