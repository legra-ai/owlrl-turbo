# owlrl-turbo

[![PyPI](https://img.shields.io/pypi/v/owlrl-turbo)](https://pypi.org/project/owlrl-turbo/)

[![Tests and wheels](https://github.com/legra-ai/owlrl-turbo/actions/workflows/ci.yml/badge.svg)](https://github.com/legra-ai/owlrl-turbo/actions/workflows/ci.yml)

[![Python line coverage](https://legra-ai.github.io/owlrl-turbo/python-lines.svg)](https://legra-ai.github.io/owlrl-turbo/)
[![Python branch coverage](https://legra-ai.github.io/owlrl-turbo/python-branches.svg)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust line coverage](https://legra-ai.github.io/owlrl-turbo/rust-lines.svg)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust region coverage](https://legra-ai.github.io/owlrl-turbo/rust-regions.svg)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust function coverage](https://legra-ai.github.io/owlrl-turbo/rust-functions.svg)](https://legra-ai.github.io/owlrl-turbo/)

Functional alpha of native RDFS and OWL-RL materialization for Python. Uses the
shared exact-term dataset runtime provided by rdflib-turbo, with native inference
extracted from pyshacl-turbo. There is no runtime dependency on Python owlrl or
pyshacl-turbo and no Python inference fallback.

Companion turbo projects: [pyshacl-turbo](https://github.com/legra-ai/pyshacl-turbo) and
[rdflib-turbo](https://github.com/legra-ai/rdflib-turbo).

```sh
uv add owlrl-turbo==0.1.0a3
```

```python
from rdflib_turbo import Dataset
from owlrl_turbo import expand

source = Dataset().parse(data='''
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <urn:Person> rdfs:subClassOf <urn:Agent> .
    <urn:alice> a <urn:Person> .
''')
expanded = expand(source, inference="rdfs")
assert bool(expanded.query('ASK { <urn:alice> a <urn:Agent> }'))
assert len(source) == 2  # the default leaves the source unchanged

# Reuse the existing dataset handle and commit only on successful inference.
expand(source, inference="owlrl", inplace=True)
```

With rdflib-turbo's shared-validation release and the matching pyshacl-turbo
release, pass `source` directly to `pyshacl_turbo.validate(source,
shacl_graph=...)`. This retains the dataset used above; only the report becomes
an RDFLib graph. The canonical [version benchmarks](https://github.com/legra-ai/pyshacl-turbo/blob/main/benchmarks/releases.md)
compare this pipeline against the three original Python libraries and historical
turbo releases. Exact wheels, dependency locks, raw timings and RSS are retained.

`expand(graph, inference="owlrl", inplace=False, destination=None)` accepts
rdflib_turbo.Dataset or RDFLib Graph/Dataset. Modes are rdfs, owlrl and both.
The return value has the input kind. Native inputs remain native between calls;
RDFLib inputs require a copy into the native runtime and conversion back.
RDFLib namespaces and blank-node identities are preserved. Named input contexts
are retained. RDFLib Dataset inference defaults to urn:owlrl-turbo:inference;
use destination to explicitly name the output graph for Dataset inputs.

Native operations release the GIL and hold a dataset lock throughout execution.
Inference commits only after successful native execution. Errors leave the source
unchanged. RDFLib inplace commits occur after native success, using RDFLib's normal
mutation API; external RDFLib stores do not acquire a new transaction guarantee.

This is **not a complete drop-in owlrl replacement**. A limited DeductiveClosure
class interface supports native axiomatic and datatype-axiom options. Custom Python rule
hooks, owl:imports loading, OWL-RL extensions
and complete inconsistency diagnostics are not exposed. Inference initialization
follows pyshacl-turbo's pinned modes. Full OWL-RL conformance and output parity
are not claimed.

Output stays within standard RDF: literal subjects and non-IRI predicates are
excluded, including generalized triples that Python owlrl may emit. Valid
literal-valued consequences remain part of the contract. Native
owl:hasKey checks every property, intentionally differing from the pinned Python
reasoner's incomplete comparison. See [ADR 0001](docs/adr/0001-inference-contract.md).

For SHACL with matching shared-runtime releases, pass the native dataset directly
to `pyshacl_turbo.validate()`. Explicit `expanded.to_rdflib()` conversion copies the
dataset. Requires Python 3.11+; rdflib-turbo supplies the native platform wheel or
builds its extension from source.

MIT OR Apache-2.0. Copyright 2026 DataRoad Inc, Delaware, USA, trading as Legra.

## Development

Development uses native uv project commands and the committed `uv.lock`.
Run `make dev` to sync the project and test tools, then `make check`. Add or update
Python dependencies with `uv add`; run Ruff, mypy and pytest through `uv run`.
Build wheels and source distributions with `uv build`. The coverage and release
harnesses create isolated uv projects and install the exact built wheels.

The [shared companion-project benchmark suite](https://github.com/legra-ai/pyshacl-turbo/blob/main/benchmarks/companions.md)
compares the three turbo projects with their reference packages, including RDFS,
OWL-RL, native/RDFLib conversion and complete SHACL pipelines. With the three
repositories as siblings, run `make benchmark-companions`. Measurements use pinned
published wheels and separate timing and peak RSS workers.

Use `make dev` and `make check`. The initial alpha is published only by the
verified GitHub Actions workflow; see [release instructions](docs/releasing.md).

Install rdflib-turbo first, then install this project with its test extra and run
`uv run --locked --extra test pytest`. Tests compare complete closures on bounded fixtures and exercise source
mutation, malformed inputs, standard RDF output and a pyshacl-turbo pipeline.

### Coverage

Coverage badges update from successful main-branch CI measurements, including the
daily scheduled run. Python lines and branches are separate; Rust badges measure
owned native source exercised by Rust and Python integration tests.
The Rust badges cover the shared rdflib-turbo runtime, including this project's tests.

CI requires 100% measured Python package line and branch coverage. Coverage is
separate from full API compatibility and standards conformance.

Rust coverage of the shared runtime is measured by
[rdflib-turbo's native coverage harness](https://github.com/legra-ai/rdflib-turbo/blob/main/docs/native-coverage.md),
including this project's Python integration tests against an instrumented native
wheel. With sibling checkouts, run `make test-rust-coverage`. owlrl-turbo has no
separate Rust implementation; the shared-runtime result is not a Python coverage
percentage or a conformance claim.

### owlrl class interface (limited compatibility)

```python
from owlrl_turbo import DeductiveClosure, OWLRL_Semantics

DeductiveClosure(OWLRL_Semantics).expand(graph)  # mutates graph; returns None
```

`RDFS_Semantics` and `RDFS_OWLRL_Semantics` are also available. Default
constructor settings use native inference. RDFLib graphs use explicit conversion;
native Dataset inputs retain their handle. Both `axiomatic_triples` and
`datatype_axioms` are forwarded to the native runtime by class and functional
entry points. `improved_datatypes=False` is accepted for the built-in semantics;
closure execution never changes RDFLib process-global converters. Custom rule
classes, process-global datatype switches, separate plain Graph
destinations and the newer Store-backed Graph inference adapter are not yet
implemented and raise explicit errors. This remains a limited compatibility
facade with the standard-RDF/hasKey boundaries described in
[ADR 0005](docs/adr/0005-deductive-closure-facade.md).

The new axiom options require the native API introduced by
[rdflib-turbo PR 41](https://github.com/legra-ai/rdflib-turbo/pull/41). The published
`0.2.0a5` artifact does not expose this API. This source change must not be released
until its dependency minimum names a published provider containing that API.
Candidate testing uses an explicit exact-wheel override.
