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
    return {triple for triple in graph.triples((None, None, None))}


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
        assert set(actual.quads()) == set(expected.quads())


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


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize(
    "lexical,datatype", [("01", "integer"), ("1.0", "decimal"), ("true", "boolean")]
)
def test_improved_datatypes_false_matches_builtin_closure_without_global_mutation(
    name, lexical, datatype
):
    from rdflib.namespace import XSD
    from rdflib.term import _toPythonMapping

    expected, actual = source("graph"), source("graph")
    literal = Literal(lexical, datatype=XSD[datatype], normalize=False)
    expected.add((EX.s, EX.p, literal))
    actual.add((EX.s, EX.p, literal))
    before = dict(_toPythonMapping)
    owlrl.DeductiveClosure(getattr(owlrl, name), improved_datatypes=False).expand(expected)
    assert dict(_toPythonMapping) == before
    closure = owlrl_turbo.DeductiveClosure(getattr(owlrl_turbo, name), improved_datatypes=False)
    assert closure.improved_datatypes is False
    closure.expand(actual)
    assert dict(_toPythonMapping) == before
    assert ordinary(actual) == ordinary(expected)


def test_mutated_improved_datatypes_option_and_noop_closure_need_no_conversion_switch():
    graph = source("graph")
    closure = owlrl_turbo.DeductiveClosure(None, improved_datatypes=False)
    assert closure.expand(graph) is None
    assert len(graph) == 2
    closure.closure_class = owlrl_turbo.RDFS_Semantics
    closure.improved_datatypes = True
    assert closure.expand(graph) is None
    assert (EX.x, RDF.type, EX.D) in graph


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("kind", ["graph", "dataset-default", "dataset-named"])
def test_direct_semantics_resolves_public_destination_during_construction(name, kind):
    for engine in (owlrl, owlrl_turbo):
        graph = source(kind)
        destination = URIRef(EX.output) if kind == "dataset-named" else None
        semantics = getattr(engine, name)(graph, True, True, destination=destination)
        assert semantics.graph is graph
        assert semantics.axioms is True and semantics.daxioms is True
        expected = (
            graph
            if kind == "graph"
            else (graph.graph(destination) if destination is not None else graph.default_graph)
        )
        assert semantics.destination.identifier == expected.identifier
        assert semantics.destination.store is expected.store
        if kind != "dataset-named":
            assert semantics.destination is expected
        if kind != "graph":
            assert graph.default_union is True


def test_direct_semantics_rejects_foreign_destination_before_execution():
    for engine in (owlrl, owlrl_turbo):
        graph = source("graph")
        with pytest.raises(ValueError, match="same backing store"):
            engine.RDFS_Semantics(graph, False, False, destination=Graph())
        assert len(graph) == 2
