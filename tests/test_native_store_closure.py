"""Native Store views execute directly without conversion to the legacy Dataset."""

import owlrl
import pytest
from rdflib import BNode, Namespace, URIRef
from rdflib import Dataset as ReferenceDataset
from rdflib import Graph as ReferenceGraph
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS
from rdflib_turbo import Dataset, Graph, Store, StoreDataset

import owlrl_turbo

EX = Namespace("urn:store-closure:")
NAMES = ["RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"]
KINDS = ["default", "named", "blank", "dataset"]


def source(kind, native):
    if kind == "dataset":
        graph = StoreDataset() if native else ReferenceDataset()
        context = graph.graph(EX.input)
    else:
        identifier = BNode("input") if kind == "blank" else EX.input
        graph = (
            Graph(bind_namespaces="none")
            if native and kind == "default"
            else Graph(Store(), identifier, bind_namespaces="none")
            if native
            else ReferenceGraph(identifier=identifier, bind_namespaces="none")
        )
        context = graph
    context.add((EX.C, RDFS.subClassOf, EX.D))
    context.add((EX.x, RDF.type, EX.C))
    context.add((EX.problem, RDF.type, OWL.Nothing))
    graph.bind("example", EX)
    return graph


def ordinary(graph):
    triples = (
        ((s, p, o) for s, p, o, _ in graph.quads())
        if isinstance(graph, ReferenceDataset)
        else graph
    )
    result = ReferenceGraph()
    for triple in triples:
        result.add(triple)
    return result


def forbid_conversion(*args, **kwargs):
    raise AssertionError("native Store input was converted to a legacy Dataset")


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize(
    "axioms,daxioms", [(False, False), (True, False), (False, True), (True, True)]
)
def test_native_semantics_flags_and_diagnostics_match_reference(
    kind, name, axioms, daxioms, monkeypatch
):
    expected, actual = source(kind, False), source(kind, True)
    reference = getattr(owlrl, name)(expected, axioms, daxioms)
    semantics = getattr(owlrl_turbo, name)(actual, axioms, daxioms)
    monkeypatch.setattr(Dataset, "from_rdflib", forbid_conversion)
    held = semantics.error_messages
    reference.closure()
    assert semantics.closure() is None
    assert semantics.error_messages is held
    assert set(semantics.error_messages) == set(reference.error_messages)
    assert isomorphic(ordinary(actual), ordinary(expected))
    assert dict(actual.namespaces()) == dict(expected.namespaces())


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("identifier", [EX.output, BNode("output")])
def test_native_separate_destination_does_not_feed_output_back(kind, name, identifier, monkeypatch):
    expected, actual = source(kind, False), source(kind, True)
    expected_destination = ReferenceGraph(expected.store, identifier)
    actual_destination = Graph(actual.store, identifier)
    before = set(actual.graph(EX.input) if kind == "dataset" else actual)
    getattr(owlrl, name)(expected, False, False, destination=expected_destination).closure()
    monkeypatch.setattr(Dataset, "from_rdflib", forbid_conversion)
    getattr(owlrl_turbo, name)(actual, False, False, destination=actual_destination).closure()
    assert isomorphic(actual_destination, ordinary(expected_destination))
    assert set(actual.graph(EX.input) if kind == "dataset" else actual) == before


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("inplace", [False, True])
@pytest.mark.parametrize("mode", ["rdfs", "owlrl", "both"])
@pytest.mark.parametrize(
    "axioms,daxioms", [(False, False), (True, False), (False, True), (True, True)]
)
def test_native_functional_expand_preserves_copy_contract(
    kind, inplace, mode, axioms, daxioms, monkeypatch
):
    graph = source(kind, True)
    before = set(ordinary(graph))
    monkeypatch.setattr(Dataset, "from_rdflib", forbid_conversion)
    result = owlrl_turbo.expand(
        graph, inference=mode, inplace=inplace, axiomatic_triples=axioms, datatype_axioms=daxioms
    )
    assert (result is graph) is inplace
    assert type(result) is type(graph)
    if kind == "dataset" and not inplace:
        assert graph.default_union is False
    assert (EX.x, RDF.type, EX.D) in ordinary(result)
    assert (dict(graph.namespaces())["example"]) == URIRef(EX)
    if not inplace:
        assert set(ordinary(graph)) == before
        assert result.store.backend is not graph.store.backend


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("abort", [False, True])
def test_native_transaction_outcome_and_namespaces_are_provisional(kind, abort):
    graph = source(kind, True)
    before, namespaces = set(ordinary(graph)), dict(graph.namespaces())
    failure = ValueError("caller abort")
    try:
        with graph.transaction() as transaction:
            semantics = owlrl_turbo.OWLRL_Semantics(transaction, False, False)
            semantics.error_messages.extend(["retained", "retained"])
            held = semantics.error_messages
            semantics.closure()
            assert semantics.error_messages is held
            assert held[:2] == ["retained", "retained"]
            assert transaction.store.backend._last_inference.error_messages == held
            assert graph.store.backend._last_inference is None
            assert dict(graph.namespaces()) == namespaces
            if abort:
                raise failure
    except ValueError as caught:
        assert abort and caught is failure
    if abort:
        assert set(ordinary(graph)) == before
        assert dict(graph.namespaces()) == namespaces


@pytest.mark.parametrize("kind", KINDS)
def test_native_none_semantics_and_invalid_custom_class_do_not_copy(kind, monkeypatch):
    graph = source(kind, True)
    before = set(ordinary(graph))
    monkeypatch.setattr(Dataset, "from_rdflib", forbid_conversion)
    assert owlrl_turbo.DeductiveClosure(None).expand(graph) is None
    assert set(ordinary(graph)) == before
    with pytest.raises(NotImplementedError, match="Custom closure"):
        owlrl_turbo.DeductiveClosure(type("Custom", (owlrl_turbo.OWLRL_Semantics,), {}))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("separate", [False, True])
def test_native_namespace_failure_preserves_history_and_aborts_pending_writes(
    kind, explicit, separate, monkeypatch
):
    graph = source(kind, True)
    before, namespaces = set(ordinary(graph)), dict(graph.namespaces())
    failure = ValueError("binding failed")
    committed_destination = Graph(graph.store, EX.failure_destination, bind_namespaces="none")
    expected_identifier = (
        EX.failure_destination
        if separate
        else (graph.default_graph.identifier if kind == "dataset" else graph.identifier)
    )
    original_bind = ReferenceGraph.bind

    def reject(owner, prefix, namespace, *args, **kwargs):
        if str(namespace) == "http://www.daml.org/2002/03/agents/agent-ont#":
            assert owner.identifier == expected_identifier
            assert set(ordinary(graph)) == before
            if separate:
                assert len(committed_destination) == 0
            # The callback can also read the staged destination through its worker.
            assert len(owner) > 0
            raise failure
        return original_bind(owner, prefix, namespace, *args, **kwargs)

    monkeypatch.setattr(ReferenceGraph, "bind", reject)

    def attempt(owner):
        destination = (
            Graph(owner.store, EX.failure_destination, bind_namespaces="none") if separate else None
        )
        semantics = owlrl_turbo.OWLRL_Semantics(owner, False, False, destination=destination)
        held = semantics.error_messages
        held.append("retained")
        with pytest.raises(ValueError) as caught:
            semantics.closure()
        assert caught.value is failure
        assert semantics.error_messages is held and held == ["retained"]
        assert owner.last_inference is None

    if explicit:
        with pytest.raises(RuntimeError, match="closed"):
            with graph.transaction() as transaction:
                attempt(transaction)
    else:
        attempt(graph)
    assert set(ordinary(graph)) == before
    assert dict(graph.namespaces()) == namespaces


@pytest.mark.parametrize("kind", KINDS)
def test_native_semantics_destination_attributes_and_union_match_reference(kind):
    graph = source(kind, True)
    semantics = owlrl_turbo.RDFS_Semantics(graph, False, False)
    assert semantics.graph is graph
    assert semantics.destination is (graph.default_graph if kind == "dataset" else graph)
    if kind == "dataset":
        assert graph.default_union is True
    for identifier in [EX.destination, BNode("destination")]:
        semantics = owlrl_turbo.RDFS_Semantics(graph, False, False, destination=identifier)
        assert isinstance(semantics.destination, Graph)
        assert semantics.destination.identifier == identifier
        assert semantics.destination.store.backend is graph.store.backend


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("inplace", [False, True])
@pytest.mark.parametrize("identifier", [EX.functional_output, BNode("functional-output")])
def test_functional_native_graph_destination_follows_the_independent_output_owner(
    kind, inplace, identifier, monkeypatch
):
    graph = source(kind, True)
    input_graph = graph.graph(EX.input) if kind == "dataset" else graph
    before = set(input_graph)
    destination = Graph(graph.store, identifier, bind_namespaces="none")
    monkeypatch.setattr(Dataset, "from_rdflib", forbid_conversion)
    result = owlrl_turbo.expand(graph, inference="rdfs", inplace=inplace, destination=destination)
    result_destination = Graph(result.store, identifier, bind_namespaces="none")
    assert (EX.x, RDF.type, EX.D) in result_destination
    assert set(input_graph) == before
    if not inplace:
        assert len(destination) == 0
        assert result_destination.store.backend is not destination.store.backend
