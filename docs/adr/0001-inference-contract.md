# ADR 0001: Share the dataset and preserve standard RDF inference

Status: Accepted for the first alpha

The inference engine is owned by rdflib-turbo's native extension. owlrl-turbo
provides the public inference entry point, operating directly on native Dataset
handles. There is one native dataset implementation and no independently built
extension pointer exchange. The alpha pins the matching runtime release exactly.

Source provenance is recorded in rdflib-turbo/vendor/README.md. Preserve the
pyshacl-turbo ADR 0021 standard RDF output boundary and its intentional owl:hasKey
correction. Exclude generalized output without concealing differences from full
reference closures. Test valid RDF closures and standards fixtures independently.

Native inference stages all changes and commits only on success. RDFLib conversion
is explicit copying, preserves caller identities and commits only after native
success; ordinary RDFLib mutations are not advertised as an external transaction.
Unknown modes and unsupported inputs raise errors. There is no Python reasoner
fallback. This alpha is a functional subset, not a drop-in replacement contract.
