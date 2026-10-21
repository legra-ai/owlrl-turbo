# ADR 0009: Parse explicit OWL imports independently of inference

Status: Accepted

Expose interpret_owl_imports and the original format constants. The helper
recursively parses imported documents through the supplied graph's parser.
Literal import targets are accepted as paths; AUTO selects syntax by the same
suffix rules as owlrl. Parsing is an explicit caller operation, never an implicit
DeductiveClosure step and never a reasoner fallback.

Match the original mutation boundary: discover a batch of import statements,
remove that batch, then parse its documents. Parser failures propagate unchanged;
earlier successful imports and removals remain visible. The transient collection
contains import statements only, not the graph relation. Cyclic imports retain
the original helper's behavior; this slice adds no traversal cache or different
cycle policy. Format-specific RDFLib plugin availability remains authoritative.

Extension semantics, custom rule classes and convert_graph are separate public
contracts and are not supplied by this helper. No new runtime capability or
released dependency minimum is asserted.
