"""The owlrl class interface over the native inference runtime."""

from rdflib import Dataset as RDFLibDataset
from rdflib import Graph, URIRef
from rdflib_turbo import Dataset


def _expand(graph, mode, destination, axioms=False, daxioms=False):
    options = {"axiomatic_triples": axioms, "datatype_axioms": daxioms}
    if getattr(graph, "_turbo_native_graph", False):
        raise NotImplementedError("Native Store Graph inference adapter is not implemented")
    if isinstance(graph, Dataset):
        if destination is not None and not isinstance(destination, (str, URIRef)):
            raise TypeError("Native Dataset destination must be an IRI")
        graph.infer(inference=mode, destination=destination, **options)
        return
    if not isinstance(graph, Graph):
        raise TypeError("Expected rdflib_turbo.Dataset or an RDFLib Graph/Dataset")
    multigraph = isinstance(graph, RDFLibDataset)
    if graph.context_aware and not multigraph:
        raise NotImplementedError("Convert context-aware graphs to rdflib.Dataset first")
    if destination is None:
        target = graph.default_graph if multigraph else graph
    elif isinstance(destination, (str, URIRef)):
        if not multigraph:
            raise ValueError("IRI destinations require a Dataset")
        target = graph.graph(URIRef(destination))
    elif isinstance(destination, Graph):
        if destination.store is not graph.store:
            raise ValueError("The source and destination graphs must share the same backing store")
        if not multigraph and destination.identifier != graph.identifier:
            raise NotImplementedError("A separate Graph destination requires snapshot rule support")
        target = destination
    else:
        raise TypeError("Expected an RDFLib Graph or IRI destination")
    # Explicit Graph conversion is an owned native inference operation. New Store
    # graphs are rejected above: their transaction context cannot be copied away.
    expanded = Dataset.from_rdflib(graph)
    if multigraph and target is not graph.default_graph:
        delta = expanded.infer_delta(inference=mode, destination=str(target.identifier), **options)
        triples = delta.to_rdflib().graph(target.identifier)
    else:
        delta = expanded.infer_delta(inference=mode, **options)
        triples = delta.to_rdflib().default_graph
    # Native inference completes before touching the caller's RDFLib store.
    for triple in triples:
        target.add(triple)
    if multigraph:
        graph.default_union = True


class _Semantics:
    _mode: str

    def __init__(self, graph, axioms, daxioms, rdfs=False, destination=None):
        self.graph = graph
        self.destination = destination
        self.axioms = axioms
        self.daxioms = daxioms
        self.rdfs = rdfs
        self.error_messages = []

    def closure(self):
        _expand(self.graph, self._mode, self.destination, self.axioms, self.daxioms)


class RDFS_Semantics(_Semantics):
    """RDFS closure, restricted to standard RDF output."""

    _mode = "rdfs"


class OWLRL_Semantics(_Semantics):
    """OWL-RL closure with the documented standard-RDF/hasKey boundaries."""

    _mode = "owlrl"


class RDFS_OWLRL_Semantics(OWLRL_Semantics, RDFS_Semantics):
    """Combined RDFS and OWL-RL closure."""

    _mode = "both"

    def __init__(self, graph, axioms, daxioms, rdfs=True, destination=None):
        super().__init__(graph, axioms, daxioms, rdfs=True, destination=destination)


def _validate_closure_class(closure_class):
    if closure_class is not None:
        if not isinstance(closure_class, type):
            raise ValueError("The closure type argument must be a class reference")
        if closure_class not in (RDFS_Semantics, OWLRL_Semantics, RDFS_OWLRL_Semantics):
            raise NotImplementedError("Custom closure class execution is not supported")


class DeductiveClosure:
    """Apply supported native semantics using owlrl's in-place class interface.

    Constructor options requiring unimplemented native configuration fail
    explicitly. This does not install modules under the original owlrl name.
    """

    improved_datatype_generic = False

    def __init__(
        self,
        closure_class,
        improved_datatypes=True,
        rdfs_closure=False,
        axiomatic_triples=False,
        datatype_axioms=False,
    ):
        _validate_closure_class(closure_class)
        self.closure_class = closure_class
        self.improved_datatypes = improved_datatypes
        self.rdfs_closure = rdfs_closure
        self.axiomatic_triples = axiomatic_triples
        self.datatype_axioms = datatype_axioms

    def expand(self, graph, destination=None):
        _validate_closure_class(self.closure_class)
        if self.closure_class is not None:
            self.closure_class(
                graph,
                self.axiomatic_triples,
                self.datatype_axioms,
                rdfs=self.rdfs_closure,
                destination=destination,
            ).closure()

    @staticmethod
    def use_improved_datatypes_conversions():
        raise NotImplementedError(
            "Process-global RDFLib datatype conversion changes are not supported"
        )

    @staticmethod
    def use_rdflib_datatypes_conversions():
        raise NotImplementedError(
            "Process-global RDFLib datatype conversion changes are not supported"
        )
