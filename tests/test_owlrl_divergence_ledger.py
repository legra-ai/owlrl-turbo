"""Compare owlrl-turbo with frozen owlrl reference closures through a closed ledger."""

import pytest
from owlrl_reference import (
    GOLDENS,
    README,
    Classifier,
    CorpusReport,
    Difference,
    DivergenceKind,
    Fixture,
    Ledger,
    Mode,
    Side,
    Statement,
    pinned_owlrl,
    readme_section,
)

FIXTURES = Fixture.corpus()


@pytest.fixture(scope="module")
def report() -> CorpusReport:
    return CorpusReport.measure(FIXTURES, Ledger.load())


def test_corpus_covers_every_rule_family():
    families = {fixture.name.split("-")[1] for fixture in FIXTURES if fixture.mode is Mode.OWLRL}
    assert {"eq", "prp", "cls", "cax", "scm", "dt"} <= families
    assert any(fixture.mode is Mode.RDFS for fixture in FIXTURES)
    assert sum("inconsistent" in fixture.name for fixture in FIXTURES) >= 4


def test_every_fixture_has_one_pinned_golden():
    assert {path.name for path in GOLDENS.glob("*.nt")} == {f.path.name for f in FIXTURES}
    for fixture in FIXTURES:
        header = fixture.golden.header()
        assert header["version"] == pinned_owlrl()
        assert Mode(header["mode"]) is fixture.mode


def test_observed_divergences_equal_the_closed_ledger(report):
    observed = report.observations()
    expected = report.ledger.expected_observations()
    assert observed - expected == frozenset(), "unlisted divergence"
    assert expected - observed == frozenset(), "ledgered divergence no longer occurs"


def test_readme_reports_current_ledger(report):
    current = readme_section(README.read_text(encoding="utf-8"))
    assert current == report.readme_block(), (
        "run: uv run --locked --extra test python tests/owlrl_reference.py"
    )


def test_ledger_without_an_observed_kind_is_not_closed(report):
    entries = tuple(
        entry
        for entry in report.ledger.entries
        if entry.kind is not DivergenceKind.HASKEY_ALL_PROPERTIES
    )
    assert report.observations() - Ledger(entries).expected_observations()


def test_unclassifiable_statement_fails():
    fixture = next(f for f in FIXTURES if f.name == "rdfs-subclass")
    stray = Statement("<urn:x>", "<urn:p>", "<urn:y>")
    difference = Difference(fixture, frozenset({stray}), frozenset())
    with pytest.raises(AssertionError, match="unclassified golden-only"):
        Classifier(difference).classify(Side.GOLDEN_ONLY, stray)
