"""Regenerate the frozen owlrl reference closures from the pinned reference reasoner.

Run only through the regeneration environment, which pins owlrl exactly:

    uv run --project tools/owlrl-goldens --locked python scripts/regenerate_owlrl_goldens.py

Each tests/owlrl-corpus/<mode>-<family>.nt fixture produces
tests/owlrl-goldens/<mode>-<family>.nt. Goldens use generalized N-Triples: one
statement per line in RDFLib's N3 term syntax, so the literal subjects that the
reference reasoner retains stay representable. Blank nodes carry RDFLib's
canonical labels and statements are sorted, making regeneration deterministic.
This script never imports owlrl_turbo; it records the reference only.
"""

import enum
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import owlrl
from rdflib import Graph
from rdflib.compare import to_canonical_graph

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "tests" / "owlrl-corpus"
GOLDENS = ROOT / "tests" / "owlrl-goldens"
PINNED_OWLRL = "7.6.2"
HEADER_PREFIX = "# owlrl-golden owlrl=="


class Mode(enum.Enum):
    RDFS = "rdfs"
    OWLRL = "owlrl"

    @property
    def semantics(self) -> type:
        if self is Mode.RDFS:
            return owlrl.RDFS_Semantics
        return owlrl.OWLRL_Semantics


@dataclass(frozen=True)
class Fixture:
    path: Path

    @property
    def mode(self) -> Mode:
        return Mode(self.path.name.split("-", 1)[0])

    @property
    def golden(self) -> Path:
        return GOLDENS / self.path.name

    def reference_closure(self) -> Graph:
        graph = Graph().parse(self.path, format="nt")
        owlrl.DeductiveClosure(self.mode.semantics).expand(graph)
        return to_canonical_graph(graph)

    def write_golden(self) -> None:
        # bounded: corpus fixtures are small hand-written rule-family examples.
        lines = sorted(" ".join(term.n3() for term in t) + " ." for t in self.reference_closure())
        body = "\n".join([f"{HEADER_PREFIX}{PINNED_OWLRL} mode={self.mode.value}", *lines])
        self.golden.write_text(body + "\n", encoding="utf-8")


def main() -> int:
    installed = version("owlrl")
    if installed != PINNED_OWLRL:
        print(f"owlrl {installed} installed; regeneration requires {PINNED_OWLRL}", file=sys.stderr)
        return 1
    GOLDENS.mkdir(exist_ok=True)
    fixtures = [Fixture(path) for path in sorted(CORPUS.glob("*.nt"))]
    expected = {fixture.golden.name for fixture in fixtures}
    for stale in GOLDENS.glob("*.nt"):
        if stale.name not in expected:
            stale.unlink()
    for fixture in fixtures:
        fixture.write_golden()
    print(f"wrote {len(fixtures)} goldens with owlrl {installed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
