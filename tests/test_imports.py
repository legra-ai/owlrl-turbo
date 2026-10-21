"""Public import parsing is separate from inference."""

import sys
from io import StringIO

import owlrl
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL

import owlrl_turbo


@pytest.mark.parametrize("constant", ["AUTO", "TURTLE", "RDFXML", "JSON", "RDFA"])
def test_format_constants(constant):
    assert getattr(owlrl_turbo, constant) == getattr(owlrl, constant)


@pytest.mark.parametrize("literal_path", [False, True])
def test_recursive_imports_match_reference(tmp_path, literal_path):
    leaf = tmp_path / "leaf.ttl"
    leaf.write_text("<urn:leaf> <urn:p> <urn:o> .")
    parent = tmp_path / "parent.ttl"
    parent.write_text(f"<urn:parent> <{OWL.imports}> <{leaf.as_uri()}> .")
    graphs = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        target = Literal(str(parent)) if literal_path else URIRef(parent.as_uri())
        graph.add((URIRef("urn:root"), OWL.imports, target))
        assert module.interpret_owl_imports(module.AUTO, graph) is None
        assert not list(graph.triples((None, OWL.imports, None)))
        graphs.append(graph)
    assert isomorphic(*graphs)
    assert len(graphs[1]) == 1


@pytest.mark.parametrize(
    ("iformat", "source", "expected"),
    [
        ("auto", "x.ttl", "turtle"),
        ("auto", "x.n3", "turtle"),
        ("auto", "x.json", "json-ld"),
        ("auto", "x.jsonld", "json-ld"),
        ("auto", "x.html", "rdfa1.1"),
        ("auto", "x.rdf", "xml"),
        ("turtle", "x.rdf", "turtle"),
        ("xml", "x.ttl", "xml"),
        ("json", "x.rdf", "json-ld"),
        ("rdfa", "x.rdf", "rdfa1.1"),
        ("auto", "-", "turtle"),
    ],
)
def test_parser_selection_and_remove_before_parse(monkeypatch, iformat, source, expected):
    stream = StringIO("input")
    monkeypatch.setattr(sys, "stdin", stream)
    observations = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        graph.add((URIRef("urn:root"), OWL.imports, Literal(source)))
        seen = []

        def parse(inp, *, format):
            assert not list(graph.triples((None, OWL.imports, None)))
            seen.append((inp, format))

        monkeypatch.setattr(graph, "parse", parse)
        module.interpret_owl_imports(iformat, graph)
        observations.append(seen)
    assert observations == [[(stream if source == "-" else source, expected)]] * 2


def test_parse_failure_preserves_exact_error_after_import_removal(monkeypatch):
    error = ValueError("invalid imported input")
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        graph.add((URIRef("urn:a"), OWL.imports, URIRef("urn:input")))
        graph.add((URIRef("urn:keep"), URIRef("urn:p"), URIRef("urn:o")))

        def fail(*args, **kwargs):
            raise error

        monkeypatch.setattr(graph, "parse", fail)
        with pytest.raises(ValueError) as caught:
            module.interpret_owl_imports(module.TURTLE, graph)
        assert caught.value is error
        assert len(graph) == 1


def test_unknown_format_error_matches_reference():
    errors = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        graph.add((URIRef("urn:a"), OWL.imports, URIRef("urn:input")))
        with pytest.raises(Exception) as caught:
            module.interpret_owl_imports("unknown", graph)
        errors.append((type(caught.value), str(caught.value)))
        assert len(graph) == 0
    assert errors[0] == errors[1]


@pytest.mark.parametrize("kind", ["reference", "graph", "dataset"])
def test_actual_relative_duplicate_imports(tmp_path, monkeypatch, kind):
    from rdflib_turbo import Graph as NativeGraph
    from rdflib_turbo import Store, StoreDataset

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.ttl").write_text("<urn:s> <urn:p> <urn:o> .")
    graph = {
        "reference": Graph,
        "graph": lambda: NativeGraph(Store()),
        "dataset": lambda: StoreDataset(Store(), default_union=True),
    }[kind]()
    for subject in ("urn:a", "urn:b"):
        graph.add((URIRef(subject), OWL.imports, Literal("data.ttl")))
    actual_parse = graph.parse
    parsed = []

    def parse(source, *, format):
        parsed.append(source)
        return actual_parse(source, format=format)

    monkeypatch.setattr(graph, "parse", parse)
    assert owlrl_turbo.interpret_owl_imports("auto", graph) is None
    assert parsed == ["data.ttl", "data.ttl"]
    assert set(graph.triples((None, None, None))) == {
        (URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o"))
    }


@pytest.mark.parametrize("length", [1, 2])
def test_cycles_raise_before_repeated_parse(tmp_path, monkeypatch, length):
    paths = [tmp_path / f"cycle{index}.ttl" for index in range(length)]
    for index, source in enumerate(paths):
        target = paths[(index + 1) % length].as_uri()
        source.write_text(f"<urn:import> <{OWL.imports}> <{target}> .")
    graph = Graph()
    graph.add((URIRef("urn:root"), OWL.imports, URIRef(paths[0].as_uri())))
    actual_parse = graph.parse
    calls = []

    def parse(inp, *, format):
        calls.append(inp)
        if len(calls) > length + 1:
            raise RuntimeError("reference repeats indefinitely")
        return actual_parse(inp, format=format)

    monkeypatch.setattr(graph, "parse", parse)
    with pytest.raises(RuntimeError, match="Cyclic OWL import"):
        owlrl_turbo.interpret_owl_imports("auto", graph)
    assert len(calls) <= length + 1


def test_acyclic_diamond_may_parse_document_more_than_once(tmp_path):
    leaf = tmp_path / "leaf.ttl"
    leaf.write_text("<urn:s> <urn:p> <urn:o> .")
    middle = tmp_path / "middle.ttl"
    middle.write_text(f"<urn:middle> <{OWL.imports}> <{leaf.as_uri()}> .")
    graphs = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        for target in (leaf, middle):
            graph.add((URIRef("urn:root"), OWL.imports, URIRef(target.as_uri())))
        module.interpret_owl_imports("auto", graph)
        graphs.append(graph)
    assert isomorphic(*graphs)


@pytest.mark.parametrize("reverse", [False, True])
def test_cycle_hidden_by_duplicate_pending_statement(tmp_path, monkeypatch, reverse):
    first, second, third = [tmp_path / f"{name}.ttl" for name in ("first", "second", "third")]
    shared = f"<urn:shared> <{OWL.imports}> <{third.as_uri()}> ."
    first.write_text(shared)
    second.write_text(shared)
    third.write_text(f"<urn:back> <{OWL.imports}> <{second.as_uri()}> .")
    graph = Graph()
    for target in [second, first] if reverse else [first, second]:
        graph.add((URIRef("urn:root"), OWL.imports, URIRef(target.as_uri())))
    actual_parse = graph.parse
    calls = []

    def parse(source, *, format):
        calls.append(source)
        if len(calls) > 8:
            raise RuntimeError("cycle was not detected")
        return actual_parse(source, format=format)

    monkeypatch.setattr(graph, "parse", parse)
    with pytest.raises(RuntimeError, match="Cyclic OWL import"):
        owlrl_turbo.interpret_owl_imports("auto", graph)


def test_uneven_overlapping_diamonds_are_not_cycles(tmp_path):
    edges = {
        "a": ["b", "c"],
        "b": ["d"],
        "c": ["d"],
        "d": ["e"],
        "e": [],
        "x1": ["x2"],
        "x2": ["x3"],
        "x3": ["x4"],
        "x4": ["z"],
        "z": ["a"],
    }
    paths = {name: tmp_path / f"{name}.ttl" for name in edges}
    for name, children in edges.items():
        content = [
            f"<urn:{name}> <{OWL.imports}> <{paths[child].as_uri()}> ." for child in children
        ]
        content.append(f"<urn:{name}> <urn:p> <urn:o> .")
        paths[name].write_text("\n".join(content))
    graphs = []
    for module in (owlrl, owlrl_turbo):
        graph = Graph()
        for target in ("a", "x1"):
            graph.add((URIRef("urn:root"), OWL.imports, URIRef(paths[target].as_uri())))
        module.interpret_owl_imports("auto", graph)
        graphs.append(graph)
    assert isomorphic(*graphs)
    assert len(graphs[1]) == len(edges)
