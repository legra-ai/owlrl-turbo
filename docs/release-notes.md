owlrl-turbo 0.2.0a1: limited compatibility alpha.

Adds the `DeductiveClosure` interface and built-in RDFS, OWL-RL and combined
semantics classes, axiom options, diagnostic history and scoped ordinary RDFLib
Graph source/destination capture. Distinct ordinary Graph endpoints must share
one backing Store; unrelated contexts are not captured. Native Graph and Dataset
inputs retain their direct inference path.

Requires the published rdflib-turbo 0.2.0a20 runtime. The compatibility facade
remains limited: custom closure classes, OWL extension semantics and global
datatype conversion switches are not implemented. Existing intentional inference
differences and standard-RDF output boundaries remain explicit in the ADRs.

Native RDFS, OWL-RL and combined inference through the shared [rdflib-turbo](https://github.com/legra-ai/rdflib-turbo) dataset runtime. Supports native and RDFLib graph/dataset inputs with explicit mutation behavior. [pyshacl-turbo](https://github.com/legra-ai/pyshacl-turbo) integration uses RDFLib conversion.

This is a limited alpha API, not a complete drop-in replacement. See the README and ADRs for scope, intentional reference differences and remaining work. No performance claim is made.

Describes pyshacl-turbo, rdflib-turbo and owlrl-turbo only as companion turbo
projects. They are independent of the Legra platform. Reuse of public legra-ai
repositories does not imply platform membership.
