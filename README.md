# owlrl-turbo

[![PyPI](https://img.shields.io/pypi/v/owlrl-turbo?style=flat)](https://pypi.org/project/owlrl-turbo/)
[![Tests and wheels](https://img.shields.io/github/actions/workflow/status/legra-ai/owlrl-turbo/ci.yml?branch=main&label=Tests%20and%20wheels&logo=github&style=flat)](https://github.com/legra-ai/owlrl-turbo/actions/workflows/ci.yml)
[![Python line coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Flegra-ai.github.io%2Fowlrl-turbo%2Fpython-lines.json&style=flat)](https://legra-ai.github.io/owlrl-turbo/)
[![Python branch coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Flegra-ai.github.io%2Fowlrl-turbo%2Fpython-branches.json&style=flat)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust line coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Flegra-ai.github.io%2Fowlrl-turbo%2Frust-lines.json&style=flat)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust region coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Flegra-ai.github.io%2Fowlrl-turbo%2Frust-regions.json&style=flat)](https://legra-ai.github.io/owlrl-turbo/)
[![Shared runtime Rust function coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Flegra-ai.github.io%2Fowlrl-turbo%2Frust-functions.json&style=flat)](https://legra-ai.github.io/owlrl-turbo/)

## Performance

### Matched public Graph pipeline

**Parse → OWL-RL → SHACL: about 11× in this measured synthetic run.**
Both arms use public Graph APIs, expand into the same source Graph and validate
in place. The Turbo trio shares one DATA owner; a separate
[non-timed ownership regression](https://github.com/legra-ai/pyshacl-turbo/blob/main/tests/test_matched_graph_sampling.py)
checks the actual shared route without adding spies to timed children.

| 1,000-literal case | Python trio (ms) | Turbo trio (ms) | Time ratio | Python peak (MiB) | Turbo peak (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Literal reflexivity | 285.2 | 25.5 | 11.2× | 88.0 | 86.1 |
| Literal typing | 362.7 | 31.5 | 11.5× | 100.5 | 98.8 |

Measured **31 October 2026**, macOS 27.0.1 (arm64), CPython **3.13.16**, native uv **0.13.5**:
original registry wheels of **rdflib-turbo 0.2.0a23 / owlrl-turbo 0.2.0a1 /
pyshacl-turbo 0.7.1**, versus **RDFLib 7.6.0 / OWL-RL 7.6.2 / pySHACL 0.40.1**.
These are medians of five fresh children per arm after a separate warmup.
The total includes Graph construction/parsing, OWL-RL closure construction/expansion and public
validation/report construction; imports, fixture text and SHAPES preparation are
outside. Complete scoped/generalized facts, literal metadata, report/text,
namespace/effect/flag gates passed for the declared normal policy (`True`).
The strict `False` scenario remains DIFFERENT with null ratios.

Peak RSS is absolute whole-process memory captured before correctness encoding;
it includes imports, setup and retained results. This single-host result is not
a universal speed or memory claim. See the portable
[numeric provenance](https://github.com/legra-ai/pyshacl-turbo/blob/main/benchmarks/matched-graph-macos-2026-10-31.json)
and [method/locked replay](https://github.com/legra-ai/pyshacl-turbo/blob/main/benchmarks/companions.md#matched-public-graph-pipelines).
From a pyshacl-turbo checkout, use a fresh output directory:

```sh
uv run --no-project --python 3.13.16 python -I -B benchmarks/matched_graph_driver.py \
    --cohort benchmarks/matched-graph-releases.json --roles baseline --widths 1000 \
    --repeats 5 --output benchmark-artifacts/matched-graph-readme
```

### Historical measurements and provenance

Compare **RDFLib + OWL-RL + pySHACL** with
[rdflib-turbo](https://github.com/legra-ai/rdflib-turbo),
[owlrl-turbo](https://github.com/legra-ai/owlrl-turbo) and
[pyshacl-turbo](https://github.com/legra-ai/pyshacl-turbo) used together.
The Turbo pipeline keeps **one native dataset** through parsing, in-place
inference and SHACL validation.

**End-to-end measurements for 1,000 synthetic nodes:**

| Platform | Inference | Python trio (ms) | Turbo trio (ms) | Python peak (MiB) | Turbo peak (MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| Linux x86-64 | RDFS | 522.5 | **47.6** | 47.15 | 68.66 |
| Linux x86-64 | OWL-RL | 801.3 | **56.4** | 48.69 | 69.29 |
| macOS ARM64 | RDFS | 702.8 | **80.7** | 55.38 | 59.94 |
| macOS ARM64 | OWL-RL | 1,028.5 | **72.5** | 55.91 | 60.42 |

**Turbo uses more memory in these runs: 8–46% higher whole-process peak RSS.**
Ordinary RDF inference closures and complete SHACL report graphs match.
Generalized RDF statements and report text differ, so these timings are
**not a full-output speedup claim** or a claim of complete drop-in parity.

Measured in CI on **21 October 2026**, using source-built wheels and Python 3.13:
`rdflib-turbo 0.2.0a7`, `owlrl-turbo 0.1.0a3`, `pyshacl-turbo 0.6.0` versus
`rdflib 7.6.0`, `owlrl 7.6.2`, `pyshacl 0.40.1`.
Times are medians of seven samples after warmup and include data parsing,
shape compilation, inference, validation and full report construction. Shapes
are parsed before timing. Memory is the median peak RSS of three fresh processes,
including the interpreter, imports and retained output. Shared CI hosts and small
synthetic cases do not establish universal speedups or large-dataset capacity.

See the complete [Linux measurements](https://github.com/legra-ai/pyshacl-turbo/blob/bc3082b44e680d8c8193407c2d1c826d80bc51d5/runs/39687798434-1/ubuntu-latest/releases.md),
[macOS measurements](https://github.com/legra-ai/pyshacl-turbo/blob/bc3082b44e680d8c8193407c2d1c826d80bc51d5/runs/39687798434-1/macos-latest/releases.md) and
[continuously recorded benchmark history](https://github.com/legra-ai/pyshacl-turbo/tree/benchmark-results)
for all samples, source identities, dependency locks and other dataset sizes.

## Overview

Functional alpha of native RDFS and OWL-RL materialization for Python. Uses the
shared exact-term dataset runtime provided by rdflib-turbo, with native inference
extracted from pyshacl-turbo. There is no runtime dependency on Python owlrl or
pyshacl-turbo and no Python inference fallback.

Companion turbo projects: [pyshacl-turbo](https://github.com/legra-ai/pyshacl-turbo) and
[rdflib-turbo](https://github.com/legra-ai/rdflib-turbo).

```sh
uv add owlrl-turbo==0.2.0a1
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
RDFLib inputs require one copy into the native runtime. Inplace calls stream only
changed rows back; nonmutating calls explicitly export their independent result.
RDFLib namespaces and blank-node identities are preserved. Named input contexts
are retained. RDFLib Dataset inference defaults to urn:owlrl-turbo:inference;
use destination to explicitly name the output graph for Dataset inputs.

Native operations release the GIL and hold a dataset lock throughout execution.
Inference commits only after successful native execution. Errors leave the source
unchanged. RDFLib inplace commits occur after native success, using RDFLib's normal
mutation API; external RDFLib stores do not acquire a new transaction guarantee.

This is **not a complete drop-in owlrl replacement**. A limited DeductiveClosure
class interface supports native axiomatic and datatype-axiom options. Custom Python rule
hooks and OWL-RL extensions
and complete inconsistency diagnostics are not exposed. Inference initialization
follows pyshacl-turbo's pinned modes. Full OWL-RL conformance and output parity
are not claimed.

Programmatic inference retains generalized RDF terms, including literal subjects.
Strict document formats retain their own syntax contracts. Explicit
`interpret_owl_imports` parsing is separate from closure execution. Native
owl:hasKey checks every property, intentionally differing from the pinned Python
reasoner's incomplete comparison. The canonical Dataset and streaming writeback
source integration still requires coordinated installed-wheel acceptance; see
[ADR 0011](docs/adr/0011-stream-private-inference-changes.md).

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
classes and process-global datatype switches are not yet implemented and raise
explicit errors. This remains a limited compatibility
facade with the standard-RDF/hasKey boundaries described in
[ADR 0005](docs/adr/0005-deductive-closure-facade.md).

The axiom options, diagnostic history and native copy/closure APIs require
published `rdflib-turbo>=0.2.0a20`. Distinct ordinary Graph source and destination
endpoints must share one backing Store; unrelated contexts are not captured.
CI installs the exact minimum from the public
registry and tests both RDFLib closure and independent native Graph expansion.
Candidate-provider testing uses a separate explicit exact-wheel override.
