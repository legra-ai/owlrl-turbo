# ADR 0005: Native execution behind the owlrl class interface

Status: Accepted for the limited compatibility facade

Expose `DeductiveClosure`, `RDFS_Semantics`, `OWLRL_Semantics` and
`RDFS_OWLRL_Semantics`. Default closure calls execute native inference, mutate
the provided graph, preserve existing namespace bindings and return `None`,
matching owlrl 7.6.2. The existing functional `expand` keeps its nonmutating default.

RDFLib Graph conversion remains explicit owned copying before native execution.
Native inference completes before writing consequences to an RDFLib destination.
Only the native inference delta is exported and inserted, requiring the published
rdflib-turbo 0.2.0a5 runtime or newer. Original statements are never decoded again
or reinserted during writeback.
This does not provide transactional guarantees for arbitrary third-party RDFLib
Store writes. Legacy native Dataset inputs retain their native handle.

The newer Store/Transaction Graph frontend is rejected until a native inference
adapter preserves its transaction and shared storage semantics. It must never be
silently converted into the older Dataset backend.

Semantics classes select the corresponding native mode. In owlrl, the
`rdfs_closure` flag is a subclass hook: setting it on OWLRL_Semantics does not turn
that class into combined semantics. Differential tests retain that behavior.

ADR 0006 supersedes the initial rejection of axiomatic/datatype flags and the
per-closure datatype conversion preference. Process-global datatype conversion
switches and custom closure classes still fail explicitly. A distinct plain Graph destination
also fails: reference rules read only the source snapshot, whereas native full
closure feeds new consequences back into subsequent rounds. Dataset destinations
can safely use native union closure and named/default output graphs.

ADR 0001's standard RDF output restriction and intentional owl:hasKey correction
remain. Matching simple standard-RDF closures does not establish general owlrl
parity. Import migration is still required; no module is installed as `owlrl`.
