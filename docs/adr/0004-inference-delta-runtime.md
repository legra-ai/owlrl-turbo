# ADR 0004: Require native inference delta support

Status: Accepted

Supersedes the minimum inference-provider version in ADR 0003.

In-place expansion of an RDFLib graph must write only newly inferred triples.
Exporting and reinserting the entire closure creates redundant RDFLib objects
and repeats writes for every input triple. The native runtime computes the
delta against the original dataset before exporting terms.

Require rdflib-turbo >=0.2.0a5,<0.3, the first published release containing
`Dataset.infer_delta`. Dependency resolution must reject older runtimes rather
than discover this missing method during expansion. Native Dataset inputs keep
their existing direct inference path. The reference Python reasoner is used
only by differential tests.
