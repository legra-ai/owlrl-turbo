"""RDFS and OWL-RL inference using rdflib-turbo's native runtime."""

from importlib.metadata import version
from typing import overload

from rdflib import BNode, Graph
from rdflib import Dataset as RDFLibDataset
from rdflib_turbo import Dataset, StoreDataset
from rdflib_turbo import Graph as NativeGraph

from ._closure import (
    DeductiveClosure,
    OWLRL_Semantics,
    RDFS_OWLRL_Semantics,
    RDFS_Semantics,
    _bind_diagnostics,
    _expand,
    _publish_changes,
    return_closure_class,
)
from ._imports import AUTO, JSON, RDFA, RDFXML, TURTLE, interpret_owl_imports

__version__ = version("owlrl-turbo")
__all__ = [
    "AUTO",
    "JSON",
    "RDFA",
    "RDFXML",
    "TURTLE",
    "DeductiveClosure",
    "OWLRL_Semantics",
    "RDFS_OWLRL_Semantics",
    "RDFS_Semantics",
    "expand",
    "interpret_owl_imports",
    "return_closure_class",
]


@overload
def expand(
    graph: NativeGraph,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | BNode | Graph | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> NativeGraph: ...


@overload
def expand(
    graph: StoreDataset,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | BNode | Graph | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> StoreDataset: ...


@overload
def expand(
    graph: RDFLibDataset,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> RDFLibDataset: ...


@overload
def expand(
    graph: Graph,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> Graph: ...


@overload
def expand(
    graph: Dataset,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> Dataset: ...


def expand(
    graph: Dataset | Graph,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | BNode | Graph | None = None,
    axiomatic_triples: bool = False,
    datatype_axioms: bool = False,
) -> Dataset | Graph:
    """Compute a native closure, returning the input kind.

    Modes are rdfs, owlrl and both. The default leaves the input unchanged.
    destination, when specified, is an IRI naming the inference output graph;
    native Graph inputs also accept exact blank identifiers and same-store Graph
    destinations. Ordinary RDFLib Graph inputs cannot select a destination. Native writes commit
    only after the complete inference operation succeeds.
    """
    options = {"axiomatic_triples": axiomatic_triples, "datatype_axioms": datatype_axioms}
    if inference not in ("rdfs", "owlrl", "both"):
        raise ValueError(f"Unknown inference mode: {inference}")
    if isinstance(graph, (NativeGraph, StoreDataset)):
        if isinstance(graph, StoreDataset) and destination is None:
            destination = "urn:owlrl-turbo:inference"
        graph._inference_scope(destination)
        result = graph if inplace else graph.copy()
        target = destination.identifier if isinstance(destination, Graph) else destination
        _expand(result, inference, target, axiomatic_triples, datatype_axioms)
        return result
    if getattr(graph, "_turbo_native_graph", False):
        raise TypeError("Expected a native Graph or StoreDataset instance")
    if not isinstance(graph, Graph):
        raise TypeError("Expected rdflib_turbo.Dataset or an RDFLib Graph/Dataset")
    multigraph = isinstance(graph, RDFLibDataset)
    if graph.context_aware and not multigraph:
        raise NotImplementedError("Convert context-aware graphs to rdflib.Dataset first")
    if destination is not None and not multigraph:
        raise ValueError("A named inference destination requires a Dataset")
    if multigraph and destination is None:
        destination = "urn:owlrl-turbo:inference"
    native_source = Dataset.from_rdflib(graph)
    if inplace:
        changes = native_source._capture_changes(
            inference=inference, destination=destination, **options
        )
        try:
            _publish_changes(graph, changes)
            _bind_diagnostics(graph, changes.outcome.error_messages)
            return graph
        finally:
            changes.close()
    expanded = native_source.infer(
        inference=inference, destination=destination, **options
    ).to_rdflib()
    return expanded if multigraph else expanded.default_graph
