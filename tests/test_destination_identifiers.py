"""Ordinary Dataset destinations retain RDFLib node normalization and domains."""

import owlrl
import pytest
from rdflib import BNode, Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

import owlrl_turbo


def source(kind):
    data = Dataset()
    data.default_graph.add((URIRef("urn:Child"), RDFS.subClassOf, URIRef("urn:Parent")))
    data.default_graph.add((URIRef("urn:item"), RDF.type, URIRef("urn:Child")))
    destination = {
        "blank": lambda: BNode("destination"),
        "uri": lambda: URIRef("urn:destination"),
        "string": lambda: "urn:destination",
        "literal": lambda: Literal("urn:destination", lang="en"),
        "graph": lambda: Graph(store=data.store, identifier=BNode("destination")),
    }[kind]()
    return data, destination


@pytest.mark.parametrize("kind", ("blank", "uri", "string", "literal", "graph"))
def test_destination_constructor_keeps_node_kind_without_registering_an_empty_graph(kind):
    expected, expected_destination = source(kind)
    actual, actual_destination = source(kind)
    reference = owlrl.RDFS_Semantics(expected, False, False, destination=expected_destination)
    candidate = owlrl_turbo.RDFS_Semantics(actual, False, False, destination=actual_destination)
    assert type(candidate.destination.identifier) is type(reference.destination.identifier)
    assert str(candidate.destination.identifier) == str(reference.destination.identifier)
    assert {context.identifier for context in actual.graphs()} == {
        context.identifier for context in expected.graphs()
    }
    assert actual.default_union is expected.default_union is True
    if kind == "graph":
        assert candidate.destination is actual_destination


@pytest.mark.parametrize("kind", ("blank", "uri", "string", "literal", "graph"))
@pytest.mark.parametrize("mode", ("RDFS_Semantics", "OWLRL_Semantics", "RDFS_OWLRL_Semantics"))
def test_destination_inference_preserves_every_physical_quad(kind, mode):
    expected, expected_destination = source(kind)
    actual, actual_destination = source(kind)
    for package, data, destination in (
        (owlrl, expected, expected_destination),
        (owlrl_turbo, actual, actual_destination),
    ):
        package.DeductiveClosure(getattr(package, mode), improved_datatypes=False).expand(
            data, destination=destination
        )
    assert set(actual.quads((None,) * 4)) == set(expected.quads((None,) * 4))
    assert {context.identifier for context in actual.graphs()} == {
        context.identifier for context in expected.graphs()
    }
