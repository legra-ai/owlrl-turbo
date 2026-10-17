"""RDFS and OWL-RL inference using rdflib-turbo's native runtime."""

from rdflib import Dataset as RDFLibDataset
from rdflib import Graph
from rdflib_turbo import Dataset

__version__ = "0.1.0a3"
__all__ = ["expand"]


def expand(graph, *, inference="owlrl", inplace=False, destination=None):
    """Compute a native closure, returning the input kind.

    Modes are rdfs, owlrl and both. The default leaves the input unchanged.
    destination, when specified, is an IRI naming the inference output graph;
    it is unavailable for ordinary RDFLib Graph inputs. Native writes commit
    only after the complete inference operation succeeds.
    """
    if inference not in ("rdfs", "owlrl", "both"):
        raise ValueError(f"Unknown inference mode: {inference}")
    if isinstance(graph, Dataset):
        result = graph if inplace else graph.copy()
        return result.infer(inference=inference, destination=destination)
    if not isinstance(graph, Graph):
        raise TypeError("Expected rdflib_turbo.Dataset or an RDFLib Graph/Dataset")
    multigraph = isinstance(graph, RDFLibDataset)
    if graph.context_aware and not multigraph:
        raise NotImplementedError("Convert context-aware graphs to rdflib.Dataset first")
    if destination is not None and not multigraph:
        raise ValueError("A named inference destination requires a Dataset")
    if multigraph and destination is None:
        destination = "urn:owlrl-turbo:inference"
    expanded = (
        Dataset.from_rdflib(graph).infer(inference=inference, destination=destination).to_rdflib()
    )
    result = expanded if multigraph else expanded.default_graph
    if inplace:
        if multigraph:
            for s, p, o, g in expanded.quads():
                target = (
                    graph.default_graph
                    if g == expanded.default_graph.identifier
                    else graph.graph(g)
                )
                target.add((s, p, o))
        else:
            graph += result
        return graph
    return result
