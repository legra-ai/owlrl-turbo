# ADR 0010: Select executable native semantics explicitly

Status: Accepted for the existing built-in modes

Expose return_closure_class with the original positional arguments and trimming
preference. OWL/RDFS selections return the corresponding native classes; disabling
both returns None. Extras have no effect when OWL is disabled, and trimming has
no effect without extension semantics, matching the original selector.

OWL extension selection fails explicitly. OWLRL_Extension requires native hasSelf
rules, restricted datatype/facet handling and rational conversion. Its trimming
subclass additionally removes inferred facts after closure. Returning one of the
existing classes for these choices would silently change valid rule semantics.
No placeholder extension class or original-Python reasoner fallback is added.
Custom rule lifecycle execution and convert_graph remain separate gaps.
