# Coverage badges

Successful main-branch CI and daily scheduled runs publish the measured reports
and badges to [GitHub Pages](https://legra-ai.github.io/owlrl-turbo/). PRs retain
artifacts without publishing; failed checks leave the last successful snapshot.
The public report identifies its measured source revision and date.

Python line and branch badges cover owlrl-turbo's own Python package, with 100%
required in CI. The Rust badges explicitly describe the shared rdflib-turbo
runtime. This project has no separate Rust implementation.

Its coverage job checks out an explicit rdflib-turbo source revision, builds an
instrumented native wheel and runs both the runtime's tests and this checkout's
OWL-RL integration suite. The combined native counters produce the shared-runtime
Rust line/region/function badges. Percentages are not summed. The publisher
requires the recorded OWL-RL revision to match the checkout that passed CI.

With the three repositories as siblings, `make test-rust-coverage` delegates to
the runtime harness. See
[the runtime methodology](https://github.com/legra-ai/rdflib-turbo/blob/main/docs/native-coverage.md).
Rust branch coverage, dependency/vendored-patch coverage and standards
conformance remain unmeasured by these badges.


The pinned runtime includes standalone Rust boundary tests as well as Python
integration tests. They exercise malformed lists, atomic inference failures,
exact keys, graph contexts and poisoned locks. Its datatype parser also carries
the shared gMonthDay leap-day correction. Unexecuted invariant/error regions
remain visible in the measured denominator; this update does not change the
badge scope or assign synthetic coverage.
