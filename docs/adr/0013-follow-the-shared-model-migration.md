# ADR 0013: Follow the provider's move onto the shared model crates

Status: Proposed; design only, see rdflib-turbo ADR 0079

owlrl-turbo has no Rust of its own. Its reasoner is rdflib-turbo's native
extension (ADR 0001, ADR 0008). rdflib-turbo ADR 0079 proposes moving that
extension's terms onto rdf-structural-model and every OWL-RL and RDFS rule
definition onto rdf-reasoning, while the provider keeps its storage, its
fixed-point scheduler and its tuned kernels until a shared executor matches
them. See [rdflib-turbo ADR 0079](https://github.com/legra-ai/rdflib-turbo/blob/main/docs/adr/0079-move-internals-onto-shared-model-crates.md).

Adopt that record's slices and gates for this package. Every slice must keep
the frozen OWL-RL 7.6.2 goldens in `tests/owlrl-goldens` unchanged and
reconcile `tests/divergences.toml` exactly, with no new entry. The
intentional `haskey-all-properties` correction stays. Slice 4 is expected to
move `language-tag-case` from gap to converged; this ledger records that
change when it happens, not before.

The Python facade, its public API and its mode selection (ADR 0005, 0006,
0010) do not change. A provider release that moves internals is adopted here
only after the published matched Graph and shared dataset benchmarks stay
within ADR 0079's budget.
