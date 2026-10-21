"""In-place RDFLib inference converts and writes only native additions."""

import json

import pytest
from rdflib import Dataset as RDFLibDataset
from rdflib import Graph
from rdflib_turbo import Dataset

from owlrl_turbo import expand

SCHEMA = """
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<urn:Class> rdfs:subClassOf <urn:Parent> .
<urn:item> a <urn:Class>; <urn:label> "original literal" .
"""


def source_graph(multigraph):
    if multigraph:
        return RDFLibDataset().parse(data="<urn:input> { " + SCHEMA + " }", format="trig")
    return Graph().parse(data=SCHEMA, format="turtle")


@pytest.mark.parametrize("multigraph", [False, True])
def test_inplace_conversion_never_decodes_original_quads(monkeypatch, multigraph):
    source = source_graph(multigraph)
    expected = expand(source, inference="rdfs")
    expected_quads = set(expected.quads()) if multigraph else set(expected)
    originals = {
        json.dumps(quad, sort_keys=True)
        for quad in json.loads(Dataset.from_rdflib(source)._native.quads_json())
    }
    original_converter = Dataset.to_rdflib
    conversions = []

    def convert_additions(dataset):
        exported = {
            json.dumps(quad, sort_keys=True) for quad in json.loads(dataset._native.quads_json())
        }
        assert not exported.intersection(originals), "Original quads reached RDFLib conversion"
        conversions.append(len(exported))
        return original_converter(dataset)

    monkeypatch.setattr(Dataset, "to_rdflib", convert_additions)
    assert expand(source, inference="rdfs", inplace=True) is source
    actual_quads = set(source.quads()) if multigraph else set(source)
    assert actual_quads == expected_quads
    assert len(conversions) == 1
    assert conversions[0] > 0


@pytest.mark.parametrize("multigraph", [False, True])
def test_inplace_never_readds_original_quads(monkeypatch, multigraph):
    source = source_graph(multigraph)
    originals = set(source.quads()) if multigraph else set(source)
    original_add = source.store.add

    def add_only_new(triple, context, quoted=False):
        if multigraph:
            quad = (*triple, context.identifier)
            assert quad not in originals, "Original quad was written again"
        else:
            assert triple not in originals, "Original triple was written again"
        return original_add(triple, context, quoted)

    monkeypatch.setattr(source.store, "add", add_only_new)
    assert expand(source, inference="rdfs", inplace=True) is source


@pytest.mark.parametrize("multigraph", [False, True])
def test_inplace_failure_preserves_original_graph(multigraph):
    source = source_graph(multigraph)
    target = source.graph("urn:input") if multigraph else source
    target.parse(
        data="<urn:Class> <http://www.w3.org/2002/07/owl#hasKey> _:broken .", format="turtle"
    )
    before = set(source.quads()) if multigraph else set(source)
    with pytest.raises(ValueError, match="Malformed RDF list"):
        expand(source, inplace=True)
    after = set(source.quads()) if multigraph else set(source)
    assert after == before
