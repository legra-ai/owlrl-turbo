"""In-place RDFLib inference converts and writes only native additions."""

import owlrl
import pytest
from rdflib import Dataset as RDFLibDataset
from rdflib import Graph, URIRef
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
def test_inplace_writeback_never_materializes_an_intermediate_dataset(monkeypatch, multigraph):
    source = source_graph(multigraph)
    expected = source_graph(multigraph)
    destination = URIRef("urn:owlrl-turbo:inference") if multigraph else None
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics, improved_datatypes=False).expand(
        expected, destination=destination
    )
    expected_quads = set(expected.quads()) if multigraph else set(expected)

    def forbid_intermediate_output(*args, **kwargs):
        raise AssertionError("Inplace writeback must stream native changes directly")

    monkeypatch.setattr(Dataset, "to_rdflib", forbid_intermediate_output)
    monkeypatch.setattr(Dataset, "infer_delta", forbid_intermediate_output)
    assert expand(source, inference="rdfs", inplace=True) is source
    actual_quads = set(source.quads()) if multigraph else set(source)
    assert actual_quads == expected_quads
    if multigraph:
        assert set(source.graphs()) == set(expected.graphs())


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
        data="<urn:Class> <http://www.w3.org/2002/07/owl#hasKey> _:broken . _:broken <http://www.w3.org/1999/02/22-rdf-syntax-ns#first> <urn:key>; <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest> _:broken .",
        format="turtle",
    )
    before = set(source.quads()) if multigraph else set(source)
    with pytest.raises(ValueError, match="recursive rdf:rest"):
        expand(source, inplace=True)
    after = set(source.quads()) if multigraph else set(source)
    assert after == before
