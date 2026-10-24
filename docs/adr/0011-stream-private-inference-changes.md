# ADR 0011: Stream private inference changes into RDFLib callers

Status: Accepted for source wiring; coordinated installed-wheel acceptance pending.

Use the provider's canonical Dataset/StoreDataset facade. Remove dispatch to the
retired Python Dataset wrapper. Native Graph and Dataset owners retain ADR 0008's
direct scoped inference and copy behavior.

Import ordinary RDFLib input once into a fresh unpublished native owner using
bounded typed records. Run native inference and obtain owning cursors over only
its final removals and additions. Stream removals before additions into the
caller's exact physical contexts, then close both cursors in finally. Do not
materialize another indexed additions Dataset or decode and reinsert the whole
input closure. Nonmutating expansion still explicitly exports its requested
independent result.

Retain generalized RDF terms in programmatic output; document formats keep their
own syntax contracts. Tests compare the complete reference relation without
literal-subject filters. No stronger transactional guarantee is claimed for
arbitrary RDFLib Store write callbacks.

The new private capture capability must exist in the tested published provider
before release requirements are promoted. Do not invent a future registry floor
or treat a candidate-wheel test as verification of the declared registry minimum.
Separate ordinary Graph destinations and complete owlrl parity remain work.
