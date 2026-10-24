# ADR 0012: Capture ordinary source and destination Graph scopes

Status: Accepted for source wiring; coordinated installed-wheel acceptance pending.

Supersede ADR 0005's rejection of distinct ordinary Graph destinations and ADR
0011's remaining-work note for this case. Original owlrl accepts Graph endpoints
that share a backing Store. Its rules read only the source scope; existing
consequences and destination-only premises never become new source premises.

Import only those two scoped triple iterators and their exact URIRef or BNode
identifiers into one fresh unpublished native owner using typed bounded records.
Retain initial destination membership so unchanged facts are never decoded and
reinserted. Use the existing explicit source/destination inference selectors and
final-change capture. Publish removals before additions to the original endpoint
objects; reject any delta outside the pair. Preserve source and destination
identifiers even when they share lexical spelling or equal the reserved Dataset
default identifier. Unrelated sibling graphs are never imported or enumerated.

Close change cursors before closing the private imported owner on every exit.
An inference/import failure precedes ordinary writeback. Arbitrary RDFLib Store
callbacks still do not acquire an external transaction guarantee: a callback
failure during writeback may leave earlier changes visible, as in ADR 0011.
Never invoke a generic caller Store commit/rollback or copy its entire contents.
Native Graph and Dataset inference retain their existing borrowed fast paths.
