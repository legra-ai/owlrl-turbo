"""Distinct ordinary Graph destinations retain exact source-only rule scope."""

import owlrl
import pytest
from rdflib import BNode, Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

import owlrl_turbo


def fixture(source_identifier, target_identifier):
    owner = Dataset()
    source = Graph(owner.store, source_identifier, bind_namespaces="none")
    target = Graph(owner.store, target_identifier, bind_namespaces="none")
    sibling = Graph(owner.store, URIRef("urn:sibling"), bind_namespaces="none")
    subject, first, second, third = map(URIRef, ("urn:x", "urn:A", "urn:B", "urn:C"))
    source.add((subject, RDF.type, first))
    source.add((first, RDFS.subClassOf, second))
    target.add((second, RDFS.subClassOf, third))
    target.add((subject, RDF.type, second))
    sibling.add((first, RDFS.subClassOf, URIRef("urn:unrelated")))
    for index in range(140):
        sibling.add((URIRef(f"urn:private:{index}"), URIRef("urn:p"), Literal(index)))
    return owner, source, target, sibling


@pytest.mark.parametrize("mode", ("RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"))
@pytest.mark.parametrize(
    ("source_identifier", "target_identifier"),
    (
        (URIRef("urn:source"), URIRef("urn:target")),
        (URIRef("urn:same"), BNode("urn:same")),
        (URIRef("urn:x-rdflib:default"), BNode("destination")),
    ),
)
def test_same_backing_graph_pair_matches_complete_original_scope(
    mode, source_identifier, target_identifier
):
    expected = fixture(source_identifier, target_identifier)
    actual = fixture(source_identifier, target_identifier)
    owlrl.DeductiveClosure(getattr(owlrl, mode)).expand(expected[1], destination=expected[2])
    assert (
        owlrl_turbo.DeductiveClosure(getattr(owlrl_turbo, mode)).expand(
            actual[1], destination=actual[2]
        )
        is None
    )
    for observed, reference in zip(actual[1:], expected[1:]):
        assert set(observed) == set(reference)
    assert (URIRef("urn:x"), RDF.type, URIRef("urn:C")) not in actual[2]


@pytest.mark.parametrize("mode", ("OWLRL_Semantics", "RDFS_OWLRL_Semantics"))
def test_pair_cleanup_preserves_destination_only_and_unrelated_physical_rows(mode):
    expected = fixture(URIRef("urn:source"), BNode("destination"))
    actual = fixture(URIRef("urn:source"), BNode("destination"))
    shared = (Literal("subject"), BNode("predicate"), Literal("object"))
    destination_only = (URIRef("urn:target-only"), BNode("other"), Literal("retained"))
    for owner, source, target, sibling in (expected, actual):
        source.add(shared)
        target.add(shared)
        target.add(destination_only)
        sibling.add(shared)
    owlrl.DeductiveClosure(getattr(owlrl, mode)).expand(expected[1], destination=expected[2])
    owlrl_turbo.DeductiveClosure(getattr(owlrl_turbo, mode)).expand(
        actual[1], destination=actual[2]
    )
    for observed, reference in zip(actual[1:], expected[1:]):
        assert set(observed) == set(reference)
    assert shared not in actual[1] and shared not in actual[2] and shared in actual[3]
    assert destination_only in actual[2]


def test_pair_import_never_scans_siblings_or_reinserts_existing_destination(monkeypatch):
    owner, source, target, _sibling = fixture(URIRef("urn:source"), URIRef("urn:target"))
    for index in range(150):
        source.add((URIRef(f"urn:source:{index}"), RDF.type, URIRef("urn:A")))
    initial = set(target)
    additions = []
    original_add, original_triples = target.add, owner.store.triples

    def add(triple):
        assert triple not in initial, "An existing destination row was decoded and reinserted"
        additions.append(triple)
        return original_add(triple)

    def triples(pattern, context=None):
        assert context is not None and context.identifier in (source.identifier, target.identifier)
        return original_triples(pattern, context)

    def serialize(*args, **kwargs):
        pytest.fail("Graph pair import used document serialization")

    monkeypatch.setattr(target, "add", add)
    monkeypatch.setattr(owner.store, "triples", triples)
    monkeypatch.setattr(Graph, "serialize", serialize)
    owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(source, destination=target)
    assert additions


def test_different_backing_store_is_rejected_before_either_import(monkeypatch):
    source, target = Graph(), Graph()

    def iterate(self):
        pytest.fail("Invalid graph pair was enumerated before validation")

    monkeypatch.setattr(Graph, "__iter__", iterate)
    with pytest.raises(ValueError, match="same backing store"):
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(source, destination=target)


@pytest.mark.parametrize("failure_stage", (None, "inference", "writeback"))
def test_pair_owner_and_change_leases_close_on_every_exit(monkeypatch, failure_stage):
    from owlrl_turbo import _closure

    _owner, source, target, _sibling = fixture(URIRef("urn:source"), URIRef("urn:target"))
    closed = []
    factory = _closure.NativeStore
    failure = RuntimeError("pair capture failure")

    class Changes:
        def __init__(self, inner):
            self.inner = inner

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def close(self):
            closed.append("changes")
            self.inner.close()

    class Owner:
        def __init__(self, inner):
            self.inner = inner

        def _infer_changes(self, *args, **kwargs):
            if failure_stage == "inference":
                raise failure
            return Changes(self.inner._infer_changes(*args, **kwargs))

        def close(self):
            closed.append("owner")
            self.inner.close()

    class Factory:
        @staticmethod
        def from_records(*args):
            return Owner(factory.from_records(*args))

    def add(triple):
        raise failure

    monkeypatch.setattr(_closure, "NativeStore", Factory)
    if failure_stage == "writeback":
        monkeypatch.setattr(target, "add", add)
    if failure_stage is None:
        owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(source, destination=target)
    else:
        with pytest.raises(RuntimeError) as raised:
            owlrl_turbo.DeductiveClosure(owlrl_turbo.RDFS_Semantics).expand(
                source, destination=target
            )
        assert raised.value is failure
    assert closed == (["owner"] if failure_stage == "inference" else ["changes", "owner"])
