"""Native diagnostic RDF and direct-Semantics message history match owlrl."""

import decimal

import owlrl
import pytest
from rdflib import RDF, Graph, Literal, Namespace
from rdflib import Dataset as ReferenceDataset
from rdflib.compare import isomorphic
from rdflib_turbo import Dataset

import owlrl_turbo

ERR = Namespace("http://www.daml.org/2002/03/agents/agent-ont#")
PREFIXES = """@prefix : <urn:diagnostic:> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""
CASES = [
    ":A owl:disjointWith :B . :x a :A, :B .",
    ":p a owl:IrreflexiveProperty . :x :p :x .",
    ":p a owl:AsymmetricProperty . :x :p :y . :y :p :x .",
    ":x owl:sameAs :y; owl:differentFrom :y .",
    ':x :p "not-an-integer"^^xsd:integer .',
    ":p owl:propertyDisjointWith :q . :x :p :y; :q :y .",
]
CLASSES = ["RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"]


def ordinary(graph):
    if isinstance(graph, Dataset):
        graph = graph.to_rdflib()
    result = Graph()
    triples = (
        ((s, p, o) for s, p, o, _ in graph.quads())
        if isinstance(graph, ReferenceDataset)
        else graph
    )
    for triple in triples:
        if not isinstance(triple[0], Literal):
            result.add(triple)
    return result


def source(document, kind):
    if kind == "native":
        return Dataset().parse(data=document)
    if kind == "dataset":
        result = ReferenceDataset()
        result.default_graph.parse(data=document, format="turtle")
        return result
    return Graph().parse(data=document, format="turtle")


@pytest.mark.parametrize("name", CLASSES)
@pytest.mark.parametrize("kind", ["graph", "dataset", "native"])
@pytest.mark.parametrize("document", CASES)
def test_direct_semantics_publishes_exact_diagnostic_rdf_and_messages(name, kind, document):
    expected = source(PREFIXES + document, "dataset" if kind == "dataset" else "graph")
    actual = source(PREFIXES + document, kind)
    reference = getattr(owlrl, name)(expected, False, False)
    native = getattr(owlrl_turbo, name)(actual, False, False)
    held = native.error_messages
    reference.closure()
    assert native.closure() is None
    assert native.error_messages is held
    assert set(native.error_messages) == set(reference.error_messages)
    assert isomorphic(ordinary(actual), ordinary(expected))
    if reference.error_messages:
        assert any(str(namespace) == str(ERR) for _, namespace in actual.namespaces())


@pytest.mark.parametrize("kind", ["graph", "dataset", "native"])
def test_prior_message_duplicates_list_identity_and_repeated_closure(kind):
    document = PREFIXES + ":x a owl:Nothing ."
    expected, actual = source(document, "graph"), source(document, kind)
    reference = owlrl.OWLRL_Semantics(expected, False, False)
    native = owlrl_turbo.OWLRL_Semantics(actual, False, False)
    for semantics in [reference, native]:
        semantics.error_messages.extend(["retained", "retained"])
        semantics.add_error("retained")
        semantics.add_error("preseeded")
    held = native.error_messages
    for count in [1, 2]:
        reference.closure()
        native.closure()
        assert native.error_messages is held
        assert native.error_messages == reference.error_messages
        assert isomorphic(ordinary(actual), ordinary(expected))
        assert len(set(ordinary(actual).subjects(RDF.type, ERR.ErrorMessage))) == count * 4


@pytest.mark.parametrize("kind", ["graph", "native"])
def test_failed_closure_preserves_caller_messages_and_does_not_publish(kind):
    actual = source(PREFIXES + ':x :p "bad"^^xsd:decimal .', kind)
    before = ordinary(actual)
    semantics = owlrl_turbo.OWLRL_Semantics(actual, False, False)
    held = semantics.error_messages
    held.append("retained")
    with pytest.raises(decimal.InvalidOperation):
        semantics.closure()
    assert semantics.error_messages is held
    assert held == ["retained"]
    assert isomorphic(ordinary(actual), before)
    assert not any(str(namespace) == str(ERR) for _, namespace in actual.namespaces())


@pytest.mark.parametrize("inplace", [False, True])
def test_functional_graph_diagnostics_and_namespace_match_reference(inplace):
    document = PREFIXES + ":x a owl:Nothing ."
    expected = source(document, "graph")
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(expected)
    actual = source(document, "graph")
    result = owlrl_turbo.expand(actual, inplace=inplace)
    assert (result is actual) is inplace
    assert isomorphic(result, ordinary(expected))
    assert any(str(namespace) == str(ERR) for _, namespace in result.namespaces())
    if not inplace:
        assert len(actual) == 1
