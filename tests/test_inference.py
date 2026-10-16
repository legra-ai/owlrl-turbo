import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
from rdflib_turbo import Dataset

from owlrl_turbo import expand

SCHEMA = "<urn:C> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <urn:D> . <urn:x> a <urn:C> ."


@pytest.mark.parametrize("mode", ["rdfs", "owlrl", "both"])
def test_native_closure_and_nonmutating_default(mode):
    dataset = Dataset().parse(data=SCHEMA)
    result = expand(dataset, inference=mode)
    assert result is not dataset
    assert len(dataset) == 2
    assert bool(result.query("ASK { <urn:x> a <urn:D> }"))


def test_native_inplace_uses_same_handle():
    dataset = Dataset().parse(data=SCHEMA)
    assert expand(dataset, inference="rdfs", inplace=True) is dataset
    assert bool(dataset.query("ASK { <urn:x> a <urn:D> }"))


def test_rdflib_graph_and_pyshacl_pipeline():
    from pyshacl_turbo import validate

    source = Graph().parse(data=SCHEMA, format="turtle")
    result = expand(source, inference="rdfs")
    assert (URIRef("urn:x"), RDF.type, URIRef("urn:D")) in result
    assert len(source) == 2
    shapes = Graph().parse(
        data="@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:shape> a sh:NodeShape; sh:targetClass <urn:D>; sh:class <urn:C> .",
        format="turtle",
    )
    assert validate(result, shacl_graph=shapes)[0]


def test_named_inference_destination_and_standard_rdf():
    dataset = Dataset().parse(
        data="<urn:g> { " + SCHEMA + ' <urn:x> <urn:p> "hello" . }', format="trig"
    )
    result = expand(dataset, inference="rdfs", destination="urn:inference")
    assert bool(result.query("ASK { GRAPH <urn:inference> { <urn:x> a <urn:D> } }"))
    assert all(not isinstance(s, Literal) for s, p, o, g in result.to_rdflib().quads())


def test_invalid_mode_fails_without_mutation():
    dataset = Dataset().parse(data=SCHEMA)
    before = dataset.serialize()
    with pytest.raises(ValueError):
        expand(dataset, inference="typo", inplace=True)
    assert dataset.serialize() == before


def test_malformed_key_does_not_commit_partial_closure():
    dataset = Dataset().parse(
        data=SCHEMA + " <urn:C> <http://www.w3.org/2002/07/owl#hasKey> _:broken ."
    )
    before = dataset.serialize()
    with pytest.raises(ValueError, match="Malformed RDF list"):
        expand(dataset, inplace=True)
    assert dataset.serialize() == before


def test_full_rdfs_closure_matches_reference_standard_rdf():
    from owlrl import DeductiveClosure, RDFS_Semantics

    source = Graph().parse(data=SCHEMA, format="turtle")
    expected = Graph()
    expected += source
    DeductiveClosure(RDFS_Semantics).expand(expected)
    ordinary = {(s, p, o) for s, p, o in expected if not isinstance(s, Literal)}
    assert set(expand(source, inference="rdfs")) == ordinary


def test_symmetric_transitive_and_all_key_properties():
    source = Dataset().parse(
        data="""
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <urn:p> a owl:SymmetricProperty, owl:TransitiveProperty .
        <urn:a> <urn:p> <urn:b> . <urn:b> <urn:p> <urn:c> .
        <urn:C> owl:hasKey ( <urn:k1> <urn:k2> ) .
        <urn:x> a <urn:C>; <urn:k1> "same"; <urn:k2> "different-x" .
        <urn:y> a <urn:C>; <urn:k1> "same"; <urn:k2> "different-y" .
    """
    )
    result = expand(source)
    assert bool(result.query("ASK { <urn:b> <urn:p> <urn:a> . <urn:a> <urn:p> <urn:c> }"))
    assert not bool(result.query("ASK { <urn:x> <http://www.w3.org/2002/07/owl#sameAs> <urn:y> }"))


def test_rdflib_dataset_context_and_inplace():
    from rdflib import Dataset as RDFLibDataset

    source = RDFLibDataset().parse(data="<urn:g> { " + SCHEMA + " }", format="trig")
    assert expand(source, inference="rdfs", inplace=True) is source
    assert (URIRef("urn:x"), RDF.type, URIRef("urn:C")) in source.graph(URIRef("urn:g"))
    assert (URIRef("urn:x"), RDF.type, URIRef("urn:D")) in source.graph(
        URIRef("urn:owlrl-turbo:inference")
    )


def test_rdflib_graph_inplace_preserves_identity():
    source = Graph().parse(data=SCHEMA, format="turtle")
    assert expand(source, inference="rdfs", inplace=True) is source
    assert (URIRef("urn:x"), RDF.type, URIRef("urn:D")) in source


def test_invalid_input_contracts():
    from rdflib import ConjunctiveGraph

    with pytest.raises(TypeError):
        expand(object())
    with pytest.raises(NotImplementedError):
        expand(ConjunctiveGraph())
    with pytest.raises(ValueError, match="requires a Dataset"):
        expand(Graph(), destination="urn:inference")
