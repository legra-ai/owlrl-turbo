"""The owlrl class interface over the native inference runtime."""

import json

from rdflib import Dataset as RDFLibDataset
from rdflib import Graph, URIRef
from rdflib_turbo import Dataset, StoreDataset
from rdflib_turbo import Graph as NativeGraph
from rdflib_turbo._native import NativeStore
from rdflib_turbo._operations import _encode
from rdflib_turbo._reads import _INPUT_TERMS, _TERM_FACTORIES


def _destination(graph, destination):
    if isinstance(graph, (NativeGraph, StoreDataset)):
        graph._inference_scope(destination)
        if isinstance(graph, StoreDataset):
            graph.default_union = True
        if destination is None:
            return graph.default_graph if isinstance(graph, StoreDataset) else graph
        if isinstance(destination, Graph):
            return destination
        return NativeGraph(store=graph.store, identifier=destination, bind_namespaces="none")
    if getattr(graph, "_turbo_native_graph", False):
        raise TypeError("Expected a native Graph or StoreDataset instance")
    if not isinstance(graph, Graph):
        raise TypeError("Expected rdflib_turbo.Dataset or an RDFLib Graph/Dataset")
    multigraph = isinstance(graph, RDFLibDataset)
    if graph.context_aware and not multigraph:
        raise NotImplementedError("Convert context-aware graphs to rdflib.Dataset first")
    if multigraph:
        graph.default_union = True
    if destination is None:
        return graph.default_graph if multigraph else graph
    if isinstance(destination, (str, URIRef)):
        if not multigraph:
            raise ValueError("IRI destinations require a Dataset")
        # Match RDFLib's identifier normalization and preserve explicit blank
        # nodes without registering an empty destination before inference runs.
        return graph.get_context(destination)
    if not isinstance(destination, Graph):
        raise TypeError("Expected an RDFLib Graph or IRI destination")
    if destination.store is not graph.store:
        raise ValueError("The source and destination graphs must share the same backing store")
    return destination


def _bind_diagnostics(graph, messages):
    if messages:
        graph.bind("err", "http://www.daml.org/2002/03/agents/agent-ont#")


def _expand(graph, mode, destination, axioms=False, daxioms=False, prior_error_messages=None):
    options = {
        "axiomatic_triples": axioms,
        "datatype_axioms": daxioms,
        "prior_error_messages": prior_error_messages,
    }
    target = _destination(graph, destination)
    if isinstance(graph, (NativeGraph, StoreDataset)):
        graph.infer(inference=mode, destination=target, **options)
        return graph.last_inference
    multigraph = isinstance(graph, RDFLibDataset)
    if not multigraph and target.identifier != graph.identifier:
        return _expand_graph_pair(graph, target, mode, axioms, daxioms, prior_error_messages)
    expanded = Dataset.from_rdflib(graph)
    changes = expanded._capture_changes(
        inference=mode,
        destination=target.identifier if multigraph else None,
        **options,
    )
    try:
        _publish_changes(graph, changes)
        _bind_diagnostics(target, changes.outcome.error_messages)
        if multigraph:
            graph.default_union = True
        return changes.outcome
    finally:
        changes.close()


def _expand_graph_pair(source, target, mode, axioms, daxioms, prior_error_messages):
    """Import only these two physical endpoints into one unpublished owner."""

    def records():
        for graph in (source, target):
            for subject, predicate, obj in graph:
                yield subject, predicate, obj, graph.identifier

    owner = NativeStore.from_records(
        records(), (source.identifier, target.identifier), _INPUT_TERMS
    )
    changes = None
    try:
        changes = owner._infer_changes(
            mode,
            (json.dumps(_encode(source.identifier)), json.dumps(_encode(target.identifier))),
            _TERM_FACTORIES,
            options=(axioms, daxioms),
            prior_error_messages=prior_error_messages,
        )
        _publish_changes(
            source, changes, endpoints={source.identifier: source, target.identifier: target}
        )
        _bind_diagnostics(target, changes.outcome.error_messages)
        return changes.outcome
    finally:
        try:
            if changes is not None:
                changes.close()
        finally:
            owner.close()


def _publish_changes(graph, changes, *, endpoints=None):
    """Stream only final changed facts; never export the whole closure."""
    multigraph = isinstance(graph, RDFLibDataset)
    for next_batch, remove in ((changes.next_removals, True), (changes.next_additions, False)):
        while True:
            rows, done = next_batch()
            for subject, predicate, obj, context in rows:
                if endpoints is not None:
                    if context not in endpoints:
                        raise RuntimeError("Unexpected inference delta outside the graph pair")
                    target = endpoints[context]
                elif multigraph:
                    target = graph.default_graph if context is None else graph.graph(context)
                elif context is None:
                    target = graph
                else:
                    raise RuntimeError("Unexpected named delta for an ordinary Graph")
                operation = target.remove if remove else target.add
                operation((subject, predicate, obj))
            if done:
                break


class _Semantics:
    _mode: str

    def __init__(self, graph, axioms, daxioms, rdfs=False, destination=None):
        self.graph = graph
        self.destination = _destination(graph, destination)
        self.axioms = axioms
        self.daxioms = daxioms
        self.rdfs = rdfs
        self.error_messages = []

    def add_error(self, message):
        """Append a newly discovered message without replacing caller-owned history."""
        if message not in self.error_messages:
            self.error_messages.append(message)

    def closure(self):
        outcome = _expand(
            self.graph,
            self._mode,
            self.destination,
            self.axioms,
            self.daxioms,
            prior_error_messages=self.error_messages,
        )
        self.error_messages[:] = outcome.error_messages


class RDFS_Semantics(_Semantics):
    """Native RDFS closure over the supplied graph scope."""

    _mode = "rdfs"


class OWLRL_Semantics(_Semantics):
    """Native OWL-RL closure over the supplied graph scope."""

    _mode = "owlrl"


class RDFS_OWLRL_Semantics(OWLRL_Semantics, RDFS_Semantics):
    """Combined RDFS and OWL-RL closure."""

    _mode = "both"

    def __init__(self, graph, axioms, daxioms, rdfs=True, destination=None):
        super().__init__(graph, axioms, daxioms, rdfs=True, destination=destination)


def return_closure_class(owl_closure, rdfs_closure, owl_extras, trimming=False):
    """Select built-in native semantics; unsupported extensions fail explicitly.

    As in owlrl, extras are ignored when OWL closure is disabled. Trimming only
    applies to extension semantics and does not alter the three built-in modes.
    """
    if owl_closure:
        if owl_extras:
            raise NotImplementedError("Native OWL extension semantics are not implemented")
        return RDFS_OWLRL_Semantics if rdfs_closure else OWLRL_Semantics
    return RDFS_Semantics if rdfs_closure else None


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
