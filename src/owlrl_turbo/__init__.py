"""RDFS and OWL-RL inference using rdflib-turbo's native runtime."""

from importlib.metadata import version
from typing import overload


from rdflib import Dataset as RDFLibDataset
from rdflib import Graph
from rdflib_turbo import Dataset

from ._closure import (
    DeductiveClosure,
    OWLRL_Semantics,
    RDFS_OWLRL_Semantics,
    RDFS_Semantics,
)

__version__ = version("owlrl-turbo")
__all__ = [
    "DeductiveClosure",
    "OWLRL_Semantics",
    "RDFS_OWLRL_Semantics",
    "RDFS_Semantics",
    "expand",
]


@overload
def expand(
    graph: RDFLibDataset,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
) -> RDFLibDataset: ...


@overload
def expand(
    graph: Graph, *, inference: str = "owlrl", inplace: bool = False, destination: str | None = None
) -> Graph: ...


@overload
def expand(
    graph: Dataset,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
) -> Dataset: ...


def expand(
    graph: Dataset | Graph,
    *,
    inference: str = "owlrl",
    inplace: bool = False,
    destination: str | None = None,
) -> Dataset | Graph:
    """Compute a native closure, returning the input kind.

    Modes are rdfs, owlrl and both. The default leaves the input unchanged.
    destination, when specified, is an IRI naming the inference output graph;
    it is unavailable for ordinary RDFLib Graph inputs. Native writes commit
    only after the complete inference operation succeeds.
    """
    if getattr(graph, "_turbo_native_graph", False):
        raise NotImplementedError("Native Store Graph inference adapter is not implemented")
    if inference not in ("rdfs", "owlrl", "both"):
        raise ValueError(f"Unknown inference mode: {inference}")
    if isinstance(graph, Dataset):
        native_result = graph if inplace else graph.copy()
        return native_result.infer(inference=inference, destination=destination)
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
        expanded = native_source.infer_delta(
            inference=inference, destination=destination
        ).to_rdflib()
    else:
        expanded = native_source.infer(inference=inference, destination=destination).to_rdflib()
    result = expanded if multigraph else expanded.default_graph
    if inplace:
        if isinstance(graph, RDFLibDataset):
            for s, p, o, g in expanded.quads():
                target = (
                    graph.default_graph
                    if g == expanded.default_graph.identifier
                    else graph.graph(g)
                )
                target.add((s, p, o))
        else:
            graph += expanded.default_graph
        return graph
    return result
