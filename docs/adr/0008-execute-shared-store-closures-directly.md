# ADR 0008: Execute native Store closures without conversion

Status: Accepted for the candidate provider API; publication waits for its release

DeductiveClosure, the three direct Semantics classes, and functional expand
accept rdflib-turbo Graph and StoreDataset owners. Forward the selected mode,
per-call axiom flags and caller-owned error history to scoped native inference.
Graph reads retain their physical scope; Dataset reads use the union and expose
the reference default_union behavior. Named and blank-node destinations retain
their exact identity. No legacy Dataset conversion or Python reasoner runs for
these owners.

Consume the owner's read-only last_inference record after success. Do not scan
error triples or bind diagnostic namespaces again: the runtime stages diagnostic
RDF, namespace metadata and its invocation outcome together. Active transaction
reports remain provisional; failure preserves caller-owned semantics history
and follows the runtime's abort boundary.

Functional expand keeps its nonmutating default. Request an independent native
copy of the selected Graph scope or every Dataset context, including empty named
graphs. Pending transaction views can be copied without committing their source.
The runtime streams directly into the new owner; no RDF document roundtrip or
Python full-graph copying is used. The original Dataset's default_union flag is
not modified by nonmutating expansion.

This supersedes ADR 0005's rejection of native Store views. Ordinary RDFLib
conversion/writeback still follows ADRs 0004 and 0007. Unsupported custom closure
classes and objects merely claiming the native marker fail explicitly. ADR 0001's
ordinary-RDF and hasKey boundaries and the initial multi-valued list ordering gap
remain. This does not establish complete owlrl parity.

The candidate requires scoped flags/history, native copy and last_inference
capabilities newer than the published dependency floor. Exact provider artifacts
validate this slice; do not publish it or invent a minimum version before an
actual provider release contains these APIs.
