"""The public selector returns the classes that native execution supports."""

import owlrl
import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

import owlrl_turbo


@pytest.mark.parametrize("owl", [False, True])
@pytest.mark.parametrize("rdfs", [False, True])
@pytest.mark.parametrize("trimming", [False, True])
def test_native_class_selection_matches_reference(owl, rdfs, trimming):
    expected = owlrl.return_closure_class(owl, rdfs, False, trimming)
    actual = owlrl_turbo.return_closure_class(owl, rdfs, False, trimming)
    assert actual is (None if expected is None else getattr(owlrl_turbo, expected.__name__))


@pytest.mark.parametrize("rdfs", [False, True])
@pytest.mark.parametrize("trimming", [False, True])
def test_extras_are_ignored_without_owl(rdfs, trimming):
    expected = owlrl.return_closure_class(False, rdfs, True, trimming)
    actual = owlrl_turbo.return_closure_class(False, rdfs, True, trimming)
    assert actual is (None if expected is None else getattr(owlrl_turbo, expected.__name__))


@pytest.mark.parametrize("rdfs", [False, True])
@pytest.mark.parametrize("trimming", [False, True])
def test_unimplemented_native_extensions_fail_explicitly(rdfs, trimming):
    with pytest.raises(NotImplementedError, match="extension"):
        owlrl_turbo.return_closure_class(True, rdfs, True, trimming)


@pytest.mark.parametrize("owl,rdfs", [(False, False), (False, True), (True, False), (True, True)])
def test_selected_class_executes_native_closure(owl, rdfs):
    graphs = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph().parse(
            data="<urn:a> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <urn:b> .",
            format="turtle",
        )
        selected = module.return_closure_class(owl, rdfs, False)
        module.DeductiveClosure(selected, rdfs_closure=rdfs).expand(graph)
        graphs.append(graph)
    assert isomorphic(*graphs)
