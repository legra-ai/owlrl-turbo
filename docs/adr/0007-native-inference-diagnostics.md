# ADR 0007: Retain native diagnostic outcomes at the class boundary

Status: Accepted; provider API published in rdflib-turbo 0.2.0a7

Inference produces ordinary RDF diagnostic nodes and a frozen invocation outcome
in the shared native runtime. The facade consumes that outcome after successful
execution; it never re-queries diagnostic triples or runs a Python reasoner.

Direct semantics preserve the identity, order and existing duplicates of the
caller-owned error_messages list. Pass its current strings as prior messages,
then replace its contents only after native inference and RDFLib writeback
succeed. add_error preserves the reference's exact-string deduplication. Repeated
closure republishes retained messages as fresh diagnostic nodes, including
messages no longer discoverable in the current input. Failed execution leaves
caller-owned history unchanged.

For RDFLib destinations, bind the reference err namespace only after successful
native execution and writeback. Native Dataset owners already bind it at their
atomic commit boundary. Arbitrary third-party RDFLib Store writes retain ADR
0005's explicit writeback atomicity limitation.

The provider carries prior_error_messages and last-inference metadata alongside
ADR 0006's per-call flags. Published rdflib-turbo 0.2.0a7 supplies these APIs and
is the dependency minimum. CI exercises that exact registry version independently
of candidate-provider wheel overrides.

Generalized RDF and the intentional hasKey correction retain ADR 0001's limits.
Initially multi-valued RDF list selection remains dependent on underlying graph
iteration order. Decimal conversion acceptance uses the native captured-context
profile, while publication of newly raised caller Decimal status flags remains
an unresolved observable contract. This slice does not claim full drop-in parity.
