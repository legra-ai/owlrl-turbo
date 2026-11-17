"""Drift check: the installed owlrl must still reproduce the frozen goldens.

This is separate from the ledger comparison, which never runs owlrl. A failure
here means the reference changed; regenerate the goldens from the pinned tools
environment and review the ledger.
"""

from importlib.metadata import version

import owlrl
import pytest
from owlrl_reference import Fixture, Mode, Statement, pinned_owlrl
from rdflib.compare import to_canonical_graph

FIXTURES = Fixture.corpus()


@pytest.mark.parametrize("fixture", FIXTURES, ids=[fixture.name for fixture in FIXTURES])
def test_installed_owlrl_reproduces_golden(fixture):
    if version("owlrl") != pinned_owlrl():
        pytest.skip(f"installed owlrl {version('owlrl')} is not the pinned reference")
    semantics = owlrl.RDFS_Semantics if fixture.mode is Mode.RDFS else owlrl.OWLRL_Semantics
    graph = fixture.source()
    owlrl.DeductiveClosure(semantics).expand(graph)
    live = frozenset(Statement.of(nodes) for nodes in to_canonical_graph(graph))
    assert live == fixture.golden.exact()
