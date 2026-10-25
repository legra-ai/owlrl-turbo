"""RDF document imports, independent from deductive inference."""

import sys

from rdflib import Graph, Literal
from rdflib.namespace import OWL

RDFXML = "xml"
TURTLE = "turtle"
JSON = "json"
AUTO = "auto"
RDFA = "rdfa"


def _parse_input(iformat, source, graph):
    if iformat == AUTO:
        if source == "-" or source.endswith((".ttl", ".n3")):
            syntax = "turtle"
        elif source.endswith((".json", ".jsonld")):
            syntax = "json-ld"
        elif source.endswith(".html"):
            syntax = "rdfa1.1"
        else:
            syntax = "xml"
    elif iformat in (TURTLE, RDFXML):
        syntax = iformat
    elif iformat == RDFA:
        syntax = "rdfa1.1"
    elif iformat == JSON:
        syntax = "json-ld"
    else:
        raise Exception("Unknown input syntax")
    graph.parse(sys.stdin if source == "-" else source, format=syntax)


def _add_dependency(dependencies, source, target):
    pending = [target]
    visited = set()
    while pending:
        current = pending.pop()
        if current == source:
            raise RuntimeError(f"Cyclic OWL import: {source} -> {target}")
        if current not in visited:
            visited.add(current)
            pending.extend(dependencies.get(current, ()))
    dependencies.setdefault(source, set()).add(target)


def interpret_owl_imports(iformat: str, graph: Graph) -> None:
    """Recursively parse imported RDF documents into graph.

    Remove each discovered batch of owl:imports statements before parsing it,
    matching owlrl. Parsing errors propagate; earlier mutations remain visible.
    DeductiveClosure does not invoke this helper automatically.
    """
    dependencies: dict[str, set[str]] = {}
    while imports := list(graph.triples((None, OWL.imports, None))):
        for statement in imports:
            graph.remove(statement)
        for _, _, target in imports:
            source = str(target)
            before = set(graph.triples((None, OWL.imports, None)))
            _parse_input(iformat, source if isinstance(target, Literal) else target, graph)
            for _, _, imported in set(graph.triples((None, OWL.imports, None))) - before:
                _add_dependency(dependencies, source, str(imported))
