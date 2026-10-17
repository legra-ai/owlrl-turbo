"""The public owlrl calling convention, with intentional RDF boundaries explicit."""

import owlrl
import pytest
from rdflib import Dataset as RDFLibDataset
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib_turbo import Dataset

import owlrl_turbo

EX = Namespace("urn:facade:")


def source():
    graph = Graph()
    graph.bind("example", EX)
    graph.add((EX.C, RDFS.subClassOf, EX.D))
    graph.add((EX.x, RDF.type, EX.C))
    return graph


@pytest.mark.parametrize("name", ["RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"])
def test_reference_constructor_mutation_return_and_complete_standard_closure(name):
    expected, actual = source(), source()
    assert owlrl.DeductiveClosure(getattr(owlrl, name)).expand(expected) is None
    closure = owlrl_turbo.DeductiveClosure(getattr(owlrl_turbo, name))
    assert closure.expand(actual) is None
    standard = {triple for triple in expected if not isinstance(triple[0], Literal)}
    assert set(actual) == standard
    assert dict(actual.namespaces())["example"] == dict(expected.namespaces())["example"]
    assert (EX.x, RDF.type, EX.D) in actual


def test_native_dataset_identity_and_none_semantics():
    graph = Dataset().parse(data="<urn:x> a <urn:C> .")
    before = graph.serialize()
    assert owlrl_turbo.DeductiveClosure(None).expand(graph) is None
    assert graph.serialize() == before
    assert owlrl_turbo.DeductiveClosure(owlrl_turbo.OWLRL_Semantics).expand(graph) is None
    assert bool(graph.query("ASK { <urn:x> a <urn:C> }"))


@pytest.mark.parametrize(
    "flag,value",
    [("axiomatic_triples", True), ("datatype_axioms", True), ("improved_datatypes", False)],
)
def test_unsupported_configuration_fails_before_mutation(flag, value):
    graph = source()
    before = set(graph)
    with pytest.raises(NotImplementedError, match=flag):
        owlrl_turbo.DeductiveClosure(owlrl_turbo.OWLRL_Semantics, **{flag: value}).expand(graph)
    assert set(graph) == before


def test_invalid_closure_type_and_custom_rules_are_not_silently_ignored():
    with pytest.raises(ValueError, match="class reference"):
        owlrl_turbo.DeductiveClosure("owlrl")
    with pytest.raises(NotImplementedError, match="closure class"):
        owlrl_turbo.DeductiveClosure(type("CustomRules", (), {}))


def test_named_dataset_default_and_explicit_destination_context():
    for destination in [None, URIRef("urn:derived")]:
        graph = RDFLibDataset()
        graph.graph(EX.g).add((EX.C, RDFS.subClassOf, EX.D))
        graph.graph(EX.g).add((EX.x, RDF.type, EX.C))
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(graph, destination)
        target = graph.default_graph if destination is None else graph.graph(destination)
        assert (EX.x, RDF.type, EX.D) in target
        assert len(graph.graph(EX.g)) == 2
        assert graph.default_union is True


def test_destination_graph_requires_same_store_and_keeps_input_untouched_on_error():
    graph, destination = source(), Graph()
    with pytest.raises(ValueError, match="same backing store"):
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(graph, destination)
    assert len(graph) == 2 and len(destination) == 0


def test_semantics_direct_closure_and_constructor_attributes():
    graph = source()
    semantics = owlrl_turbo.RDFS_Semantics(graph, False, False)
    assert semantics.graph is graph
    assert semantics.axioms is False and semantics.daxioms is False
    assert semantics.closure() is None
    assert (EX.x, RDF.type, EX.D) in graph
    closure = owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics)
    assert closure.closure_class is owlrl_turbo.RDFS_Semantics
    assert closure.improved_datatypes is True
    assert closure.axiomatic_triples is False


def test_failure_atomicity_on_malformed_list():
    graph = source()
    graph.parse(data="<urn:C> <http://www.w3.org/2002/07/owl#hasKey> _:broken .", format="turtle")
    before = set(graph)
    with pytest.raises(ValueError, match="Malformed RDF list"):
        owlrl_turbo.DeductiveClosure(owlrl_turbo.OWLRL_Semantics).expand(graph)
    assert set(graph) == before


@pytest.mark.parametrize("name", ["RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"])
def test_rdfs_constructor_flag_obeys_actual_semantics_class(name):
    expected, actual = source(), source()
    owlrl.DeductiveClosure(getattr(owlrl, name), rdfs_closure=True).expand(expected)
    owlrl_turbo.DeductiveClosure(getattr(owlrl_turbo, name), rdfs_closure=True).expand(actual)
    assert set(actual) == {t for t in expected if not isinstance(t[0], Literal)}


def test_separate_plain_graph_destination_requires_snapshot_rule_support():
    expected, actual = source(), source()
    expected_dest = Graph(store=expected.store, identifier=EX.destination)
    actual_dest = Graph(store=actual.store, identifier=EX.destination)
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(expected, expected_dest)
    assert (EX.x, RDF.type, EX.D) in expected_dest
    with pytest.raises(NotImplementedError, match="separate Graph destination"):
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(actual, actual_dest)
    assert len(actual) == 2 and len(actual_dest) == 0


@pytest.mark.parametrize(
    "kind",
    [
        "native-view",
        "native-destination",
        "wrong-input",
        "context-aware",
        "iri-graph",
        "destination-object",
    ],
)
def test_invalid_graph_and_destination_contracts(kind):
    closure = owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics)
    if kind == "native-view":

        class StoreView(Graph):
            _turbo_native_graph = True

        with pytest.raises(NotImplementedError, match="adapter"):
            closure.expand(StoreView())
    elif kind == "native-destination":
        with pytest.raises(TypeError, match="IRI"):
            closure.expand(Dataset(), Graph())
    elif kind == "wrong-input":
        with pytest.raises(TypeError, match="Expected"):
            closure.expand(object())
    elif kind == "context-aware":
        from rdflib import ConjunctiveGraph

        with pytest.raises(NotImplementedError, match="context-aware"):
            closure.expand(ConjunctiveGraph())
    elif kind == "iri-graph":
        with pytest.raises(ValueError, match="require a Dataset"):
            closure.expand(source(), "urn:dest")
    else:
        with pytest.raises(TypeError, match="destination"):
            closure.expand(source(), object())


def test_explicit_destination_graph_with_dataset_store():
    graph = RDFLibDataset()
    graph.graph(EX.input).add((EX.C, RDFS.subClassOf, EX.D))
    graph.graph(EX.input).add((EX.x, RDF.type, EX.C))
    destination = graph.graph(EX.destination)
    owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(graph, destination)
    assert (EX.x, RDF.type, EX.D) in destination
    assert len(graph.graph(EX.input)) == 2


@pytest.mark.parametrize(
    "name", ["use_improved_datatypes_conversions", "use_rdflib_datatypes_conversions"]
)
def test_global_datatype_conversion_switches_fail_explicitly(name):
    with pytest.raises(NotImplementedError, match="Process-global"):
        getattr(owlrl_turbo.DeductiveClosure, name)()


def test_explicit_destination_is_same_graph():
    graph = source()
    owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(graph, graph)
    assert (EX.x, RDF.type, EX.D) in graph


def test_native_dataset_named_destination():
    graph = Dataset().parse(
        data="<urn:g> { <urn:x> a <urn:C> . <urn:C> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <urn:D> . }",
        format="trig",
    )
    assert (
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(graph, URIRef("urn:dest"))
        is None
    )
    assert bool(graph.query("ASK { GRAPH <urn:dest> { <urn:x> a <urn:D> } }"))


def test_functional_expand_does_not_copy_native_store_views():
    class StoreView(Graph):
        _turbo_native_graph = True

    with pytest.raises(NotImplementedError, match="adapter"):
        owlrl_turbo.expand(StoreView())


def test_mutated_configuration_is_validated_when_executed():
    graph = source()
    closure = owlrl_turbo.DeductiveClosure(owlrl_turbo.OWLRL_Semantics)
    closure.improved_datatypes = False
    with pytest.raises(NotImplementedError, match="improved_datatypes"):
        closure.expand(graph)
    semantics = owlrl_turbo.OWLRL_Semantics(graph, False, False)
    semantics.axioms = True
    with pytest.raises(NotImplementedError, match="axiomatic_triples"):
        semantics.closure()
    assert len(graph) == 2


@pytest.mark.parametrize("destination", [None, URIRef("urn:derived")])
def test_complete_dataset_closure_contexts_match_reference(destination):
    expected, actual = RDFLibDataset(), RDFLibDataset()
    for graph in [expected, actual]:
        graph.graph(EX.g).add((EX.C, RDFS.subClassOf, EX.D))
        graph.graph(EX.g).add((EX.x, RDF.type, EX.C))
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(expected, destination)
    owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(actual, destination)
    ordinary = {q for q in expected.quads() if not isinstance(q[0], Literal)}
    assert set(actual.quads()) == ordinary


def test_mutated_closure_class_cannot_execute_reference_python_reasoner():
    graph = source()
    closure = owlrl_turbo.DeductiveClosure(owlrl_turbo.OWLRL_Semantics)
    closure.closure_class = owlrl.OWLRL_Semantics
    with pytest.raises(NotImplementedError, match="closure class"):
        closure.expand(graph)
    assert len(graph) == 2


def test_combined_semantics_inherits_both_and_forces_rdfs():
    assert issubclass(owlrl_turbo.RDFS_OWLRL_Semantics, owlrl_turbo.RDFS_Semantics)
    assert issubclass(owlrl_turbo.RDFS_OWLRL_Semantics, owlrl_turbo.OWLRL_Semantics)
    assert owlrl_turbo.RDFS_OWLRL_Semantics(source(), False, False, rdfs=False).rdfs is True
