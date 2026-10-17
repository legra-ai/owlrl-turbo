# ADR 0003: Permit the dataset-owned SHACL runtime

Status: Accepted

Inference already forwards native Dataset objects directly to their owning
runtime. Permit rdflib-turbo >=0.1.0a2,<0.3 so the 0.2.0a1 runtime can retain the
same object through SHACL validation too. Keep the existing in-place/copy and
atomic inference contracts. This project adds no Python SHACL implementation.

The canonical cross-wheel tests and release benchmarks live in pyshacl-turbo.
They install all three exact wheels into an isolated uv project, prohibit dataset
conversion inside the shared pipeline, and record versions, native hashes,
timings, RSS and full report/closure comparisons. The old runtime remains a
supported inference provider; validation requires the explicitly versioned
new runtime protocol and fails on unsupported versions rather than converting.
