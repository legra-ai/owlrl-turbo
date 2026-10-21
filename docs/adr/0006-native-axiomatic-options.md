# ADR 0006: Forward axiomatic options without global datatype mutation

Status: Accepted for the candidate native API; publication waits for its release

Forward `axiomatic_triples` and `datatype_axioms` to native inference for all
three semantics classes, `DeductiveClosure`, and functional `expand`. Preserve
class flags as mutable public state and read them at execution. Existing native
mutation/delta and RDFLib writeback boundaries remain unchanged. No Python
reasoner executes as a fallback.

Accept the per-instance `improved_datatypes` preference, including False. In
owlrl 7.6.2 this option switches RDFLib's global converter map around a closure;
built-in datatype checks separately call the alternative converter table
regardless of the preference. Built-in rules construct only plain error-message
literals. Fresh-process reference comparisons cover valid, invalid, lexical,
unknown, binary and temporal datatype cases with both preference values. Preserve
the preference attribute without changing process-global conversion state. The
explicit global-switch methods remain unsupported.

This supersedes ADR 0005's rejection of these constructor options. Generalized
RDF output and the intentional hasKey correction retain ADR 0001's boundaries.
Diagnostic outcomes and shared Store ownership remain separate runtime work.

The candidate requires the native flags API introduced by rdflib-turbo PR 41.
Published rdflib-turbo 0.2.0a5 lacks it. Tests use an exact candidate wheel override;
publishing requires an actual provider release and an accurate dependency minimum.
Do not claim the unreleased API is supplied by the existing dependency range.
