from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from ebb.walk import scan_repo

GOLDEN_DIR = (Path(__file__).resolve().parents[1] / "golden").resolve()
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "golden_manifest.yaml"

# CLAUDE_CODE_PLAN.md Session 7: "a CI assertion that fails below precision 0.95 or recall
# 0.85." These are the floor, not a target — never lower them to make this test pass; if a
# detector falls short, the detector is what changes (see patterns.py's own commit history).
PRECISION_FLOOR = 0.95
RECALL_FLOOR = 0.85

MatchKey = tuple[str, int, str]


def _detector_of(relative_path: str) -> str:
    return relative_path.split("/", 1)[0]


def _load_expected() -> dict[str, Counter[MatchKey]]:
    entries = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or []
    by_detector: dict[str, Counter[MatchKey]] = defaultdict(Counter)
    for entry in entries:
        key: MatchKey = (entry["path"], entry["line"], entry["matched_text"])
        by_detector[_detector_of(entry["path"])][key] += 1
    return by_detector


def _load_actual() -> dict[str, Counter[MatchKey]]:
    by_detector: dict[str, Counter[MatchKey]] = defaultdict(Counter)
    for match in scan_repo(GOLDEN_DIR):
        relative_path = str(match.path.relative_to(GOLDEN_DIR))
        key: MatchKey = (relative_path, match.line, match.matched_text)
        by_detector[_detector_of(relative_path)][key] += 1
    return by_detector


@dataclass(frozen=True)
class DetectorScore:
    detector: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float | None:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else None


def _score(
    expected: dict[str, Counter[MatchKey]], actual: dict[str, Counter[MatchKey]]
) -> list[DetectorScore]:
    """Per-detector, never pooled into one aggregate: a detector with 0/10 correct must not be
    averaged away by seven detectors running at 10/10 (CLAUDE_CODE_PLAN.md's explicit warning:
    "an average must never hide one broken detector")."""
    scores = []
    for detector in sorted(set(expected) | set(actual)):
        exp, act = expected.get(detector, Counter()), actual.get(detector, Counter())
        scores.append(
            DetectorScore(
                detector=detector,
                true_positives=sum((exp & act).values()),
                false_positives=sum((act - exp).values()),
                false_negatives=sum((exp - act).values()),
            )
        )
    return scores


def _format_report(scores: list[DetectorScore]) -> str:
    header = f"{'detector':<12}{'TP':>4}{'FP':>4}{'FN':>4}{'precision':>12}{'recall':>10}"
    rows = [header, "-" * len(header)]
    for s in scores:
        precision = f"{s.precision:.3f}" if s.precision is not None else "n/a"
        recall = f"{s.recall:.3f}" if s.recall is not None else "n/a"
        rows.append(
            f"{s.detector:<12}{s.true_positives:>4}{s.false_positives:>4}{s.false_negatives:>4}"
            f"{precision:>12}{recall:>10}"
        )
    return "\n".join(rows)


def test_every_detector_meets_the_accuracy_floor() -> None:
    scores = _score(_load_expected(), _load_actual())
    report = _format_report(scores)
    print("\n" + report)

    violations = [
        f"{s.detector}: precision {s.precision:.3f} < floor {PRECISION_FLOOR}"
        for s in scores
        if s.precision is not None and s.precision < PRECISION_FLOOR
    ] + [
        f"{s.detector}: recall {s.recall:.3f} < floor {RECALL_FLOOR}"
        for s in scores
        if s.recall is not None and s.recall < RECALL_FLOOR
    ]
    if violations:
        pytest.fail(f"\n{report}\n\nBelow the accuracy floor:\n" + "\n".join(violations))


def test_every_fixture_group_has_a_pure_decoy_case() -> None:
    """A detector could pass the floor above by never being tempted — if every fixture in a
    group only contains true positives, an over-eager regex would never be caught (0 FP is
    trivial when nothing false is ever offered). Every detector must have at least one fixture
    contributing 0 expected matches, so a false positive there is actually possible to observe."""
    expected = _load_expected()
    fixture_dirs_with_zero_expected: dict[str, set[str]] = defaultdict(set)
    for detector_dir in sorted(GOLDEN_DIR.iterdir()):
        if not detector_dir.is_dir():
            continue
        expected_paths = {key[0] for key in expected.get(detector_dir.name, Counter())}
        for fixture_dir in sorted(detector_dir.iterdir()):
            if not fixture_dir.is_dir():
                continue
            has_expected = any(
                p.startswith(f"{detector_dir.name}/{fixture_dir.name}/") for p in expected_paths
            )
            if not has_expected:
                fixture_dirs_with_zero_expected[detector_dir.name].add(fixture_dir.name)

    missing = [d for d in expected if not fixture_dirs_with_zero_expected.get(d)]
    assert not missing, f"detector groups with no pure-decoy fixture: {missing}"
