# ADR 0006: Forward axiomatic options without global datatype mutation

Status: Accepted; provider API published in rdflib-turbo 0.2.0a7

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

The native flags API introduced by rdflib-turbo PR 41 is available in published
0.2.0a7, which is the dependency minimum. CI independently exercises that exact
registry version; candidate-provider tests retain their exact-wheel override.
