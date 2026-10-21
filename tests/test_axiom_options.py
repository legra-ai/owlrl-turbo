"""Axiomatic options execute the candidate native runtime against owlrl 7.6.2."""

import owlrl
import pytest
from rdflib import Dataset as RDFLibDataset
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib_turbo import Dataset

import owlrl_turbo

EX = Namespace("urn:axiom-options:")
NAMES = ["RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"]


def source(kind):
    graph = Graph() if kind == "graph" else RDFLibDataset()
    target = graph if kind == "graph" else graph.graph(EX.input)
    target.add((EX.C, RDFS.subClassOf, EX.D))
    target.add((EX.x, RDF.type, EX.C))
    return graph


def ordinary(graph):
    return {
        triple for triple in graph.triples((None, None, None)) if not isinstance(triple[0], Literal)
    }


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize(
    "axioms,daxioms", [(False, False), (True, False), (False, True), (True, True)]
)
@pytest.mark.parametrize("kind", ["graph", "dataset-default", "dataset-named"])
def test_closure_axiomatic_options_match_complete_reference(name, axioms, daxioms, kind):
    expected, actual = source(kind), source(kind)
    destination = URIRef(EX.output) if kind == "dataset-named" else None
    for engine, graph in [(owlrl, expected), (owlrl_turbo, actual)]:
        closure = engine.DeductiveClosure(
            getattr(engine, name), axiomatic_triples=axioms, datatype_axioms=daxioms
        )
        assert closure.axiomatic_triples is axioms
        assert closure.datatype_axioms is daxioms
        assert closure.expand(graph, destination) is None
    if kind == "graph":
        assert ordinary(actual) == ordinary(expected)
    else:
        assert set(actual.quads()) == {q for q in expected.quads() if not isinstance(q[0], Literal)}


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize(
    "axioms,daxioms", [(False, False), (True, False), (False, True), (True, True)]
)
def test_direct_semantics_mutable_flags_are_forwarded(name, axioms, daxioms):
    expected, actual = source("graph"), source("graph")
    for engine, graph in [(owlrl, expected), (owlrl_turbo, actual)]:
        semantics = getattr(engine, name)(graph, False, False)
        semantics.axioms, semantics.daxioms = axioms, daxioms
        assert semantics.graph is graph
        assert semantics.closure() is None
    assert ordinary(actual) == ordinary(expected)


@pytest.mark.parametrize("inference,name", list(zip(["rdfs", "owlrl", "both"], NAMES)))
@pytest.mark.parametrize("destination", [None, str(EX.output)])
def test_functional_native_options_preserve_nonmutating_default(inference, name, destination):
    graph = Dataset.from_rdflib(source("graph"))
    original = set(graph.to_rdflib().quads())
    result = owlrl_turbo.expand(
        graph,
        inference=inference,
        destination=destination,
        axiomatic_triples=True,
        datatype_axioms=True,
    )
    assert result is not graph
    assert set(graph.to_rdflib().quads()) == original
    expected = source("graph")
    owlrl.DeductiveClosure(
        getattr(owlrl, name), axiomatic_triples=True, datatype_axioms=True
    ).expand(expected)
    converted = result.to_rdflib()
    converted.default_union = True
    assert ordinary(converted) == ordinary(expected)
