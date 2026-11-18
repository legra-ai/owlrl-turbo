"""Typed access to the frozen owlrl reference corpus, goldens and divergence ledger.

Fixtures and goldens are small hand-written rule-family examples, so the
closures held here are bounded by the corpus, not by caller data.
"""

from __future__ import annotations

import enum
import re
import tomllib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from rdflib import OWL, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.term import Node
from rdflib.util import from_n3

import owlrl_turbo

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
CORPUS = TESTS / "owlrl-corpus"
GOLDENS = TESTS / "owlrl-goldens"
LEDGER = TESTS / "divergences.toml"
README = ROOT / "README.md"
GOLDEN_TOOLS = ROOT / "tools" / "owlrl-goldens" / "pyproject.toml"
HEADER = re.compile(r"# owlrl-golden owlrl==(?P<version>\S+) mode=(?P<mode>\S+)")
TERM = re.compile(r'<[^>]*>|_:\S+|"(?:[^"\\]|\\.)*"(?:@[A-Za-z0-9-]+|\^\^<[^>]*>)?')

Nodes = tuple[Node, Node, Node]


@dataclass(frozen=True, order=True)
class Statement:
    """A statement compared by exact term spelling.

    RDFLib literal equality ignores language-tag case, which would hide a
    difference a drop-in replacement must not have; N3 spelling does not.
    """

    subject: str
    predicate: str
    object: str

    @classmethod
    def of(cls, nodes: Iterable[Node]) -> Statement:
        subject, predicate, obj = (node.n3() for node in nodes)
        return cls(subject, predicate, obj)

    @property
    def nodes(self) -> Nodes:
        return (from_n3(self.subject), from_n3(self.predicate), from_n3(self.object))  # type: ignore[return-value]

    def __str__(self) -> str:
        return f"{self.subject} {self.predicate} {self.object} ."


class Mode(enum.Enum):
    RDFS = "rdfs"
    OWLRL = "owlrl"

    @property
    def turbo_semantics(self) -> type:
        if self is Mode.RDFS:
            return owlrl_turbo.RDFS_Semantics
        return owlrl_turbo.OWLRL_Semantics


class Status(enum.Enum):
    INTENTIONAL = "intentional"
    GAP = "gap"
    CONVERGED = "converged"


class DivergenceKind(enum.Enum):
    HASKEY_ALL_PROPERTIES = "haskey-all-properties"
    LANGUAGE_TAG_CASE = "language-tag-case"
    GENERALIZED_RDF_EXCLUSION = "generalized-rdf-exclusion"
    DATATYPE_VALUE = "datatype-value"


class Side(enum.Enum):
    GOLDEN_ONLY = "golden-only"
    TURBO_ONLY = "turbo-only"


@dataclass(frozen=True)
class LedgerEntry:
    kind: DivergenceKind
    status: Status
    rule: str
    spec: str
    adr: str
    fixtures: frozenset[str]
    summary: str

    FIELDS = frozenset({"kind", "status", "rule", "spec", "adr", "fixtures", "summary"})

    @classmethod
    def from_toml(cls, table: dict[str, object]) -> LedgerEntry:
        if set(table) != cls.FIELDS:
            raise ValueError(f"ledger entry fields {sorted(table)} != {sorted(cls.FIELDS)}")
        fixtures = table["fixtures"]
        if not isinstance(fixtures, list):
            raise ValueError("ledger fixtures must be a list")
        entry = cls(
            kind=DivergenceKind(table["kind"]),
            status=Status(table["status"]),
            rule=str(table["rule"]),
            spec=str(table["spec"]),
            adr=str(table["adr"]),
            fixtures=frozenset(str(name) for name in fixtures),
            summary=str(table["summary"]),
        )
        entry.validate()
        return entry

    def validate(self) -> None:
        if not self.spec.startswith("https://www.w3.org/TR/"):
            raise ValueError(f"{self.kind.value}: spec must cite a W3C recommendation")
        if (
            not self.adr.startswith("https://github.com/legra-ai/")
            and not (ROOT / self.adr).is_file()
        ):
            raise ValueError(f"{self.kind.value}: ADR link {self.adr} does not resolve")
        if (self.status is Status.CONVERGED) != (not self.fixtures):
            raise ValueError(f"{self.kind.value}: only converged entries list no fixtures")

    def observations(self) -> frozenset[Observation]:
        return frozenset(Observation(self.kind, fixture) for fixture in self.fixtures)


@dataclass(frozen=True)
class Ledger:
    entries: tuple[LedgerEntry, ...]

    @classmethod
    def load(cls, path: Path = LEDGER) -> Ledger:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        if set(document) != {"divergence"}:
            raise ValueError("ledger holds only [[divergence]] tables")
        entries = tuple(LedgerEntry.from_toml(table) for table in document["divergence"])
        kinds = [entry.kind for entry in entries]
        if len(set(kinds)) != len(kinds):
            raise ValueError("ledger kinds must be unique")
        return cls(entries)

    def expected_observations(self) -> frozenset[Observation]:
        return frozenset().union(*(entry.observations() for entry in self.entries))

    def remaining(self) -> tuple[LedgerEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status is not Status.CONVERGED)


@dataclass(frozen=True)
class Observation:
    kind: DivergenceKind
    fixture: str


@dataclass(frozen=True)
class GoldenClosure:
    path: Path

    def header(self) -> re.Match[str]:
        with self.path.open(encoding="utf-8") as stream:
            match = HEADER.fullmatch(stream.readline().rstrip("\n"))
        if match is None:
            raise ValueError(f"{self.path.name}: missing owlrl-golden header")
        return match

    def statements(self) -> Iterator[Nodes]:
        with self.path.open(encoding="utf-8") as stream:
            next(stream)
            for line in stream:
                terms = TERM.findall(line)
                if len(terms) != 3 or not line.rstrip().endswith(" ."):
                    raise ValueError(f"{self.path.name}: malformed statement {line!r}")
                yield tuple(from_n3(term) for term in terms)  # type: ignore[misc]

    def graph(self) -> Graph:
        graph = Graph()
        for statement in self.statements():
            graph.add(statement)
        return to_canonical_graph(graph)

    def exact(self) -> frozenset[Statement]:
        return frozenset(Statement.of(nodes) for nodes in self.graph())


@dataclass(frozen=True)
class Fixture:
    path: Path

    @classmethod
    def corpus(cls) -> tuple[Fixture, ...]:
        return tuple(cls(path) for path in sorted(CORPUS.glob("*.nt")))

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def mode(self) -> Mode:
        return Mode(self.name.split("-", 1)[0])

    @property
    def golden(self) -> GoldenClosure:
        return GoldenClosure(GOLDENS / self.path.name)

    def source(self) -> Graph:
        return Graph().parse(self.path, format="nt")

    def turbo_closure(self) -> Graph:
        graph = self.source()
        owlrl_turbo.DeductiveClosure(self.mode.turbo_semantics).expand(graph)
        return to_canonical_graph(graph)

    def difference(self) -> Difference:
        golden = self.golden.exact()
        turbo = frozenset(Statement.of(nodes) for nodes in self.turbo_closure())
        return Difference(self, frozenset(golden - turbo), frozenset(turbo - golden))


@dataclass(frozen=True)
class Difference:
    fixture: Fixture
    golden_only: frozenset[Statement]
    turbo_only: frozenset[Statement]

    @property
    def exact(self) -> bool:
        return not self.golden_only and not self.turbo_only

    def sided(self) -> Iterator[tuple[Side, Statement]]:
        for statement in sorted(self.golden_only):
            yield Side.GOLDEN_ONLY, statement
        for statement in sorted(self.turbo_only):
            yield Side.TURBO_ONLY, statement

    def opposite(self, side: Side) -> frozenset[Statement]:
        return self.turbo_only if side is Side.GOLDEN_ONLY else self.golden_only

    def key_equated(self) -> frozenset[str]:
        if not any(True for _ in self.fixture.source().triples((None, OWL.hasKey, None))):
            return frozenset()
        same_as = OWL.sameAs.n3()
        return frozenset(
            term
            for statement in self.golden_only
            if statement.predicate == same_as and statement.subject != statement.object
            for term in (statement.subject, statement.object)
        )

    def observations(self) -> frozenset[Observation]:
        classifier = Classifier(self)
        kinds = {classifier.classify(side, statement) for side, statement in self.sided()}
        return frozenset(Observation(kind, self.fixture.name) for kind in kinds)


@dataclass(frozen=True)
class Classifier:
    difference: Difference

    def classify(self, side: Side, statement: Statement) -> DivergenceKind:
        if self.is_language_tag_case(side, statement):
            return DivergenceKind.LANGUAGE_TAG_CASE
        subject, predicate, _object = nodes = statement.nodes
        if isinstance(subject, Literal) or not isinstance(predicate, URIRef):
            return DivergenceKind.GENERALIZED_RDF_EXCLUSION
        if self.difference.key_equated() & {statement.subject, statement.object}:
            return DivergenceKind.HASKEY_ALL_PROPERTIES
        if any(isinstance(term, Literal) and term.datatype is not None for term in nodes):
            return DivergenceKind.DATATYPE_VALUE
        raise AssertionError(
            f"{self.difference.fixture.name}: unclassified {side.value} statement {statement}"
        )

    def is_language_tag_case(self, side: Side, statement: Statement) -> bool:
        if not any(isinstance(term, Literal) and term.language for term in statement.nodes):
            return False
        folded = fold_language(statement)
        return any(fold_language(other) == folded for other in self.difference.opposite(side))


def fold_language(statement: Statement) -> Statement:
    return Statement.of(
        Literal(term, lang=term.language.lower())
        if isinstance(term, Literal) and term.language
        else term
        for term in statement.nodes
    )


@dataclass(frozen=True)
class CorpusReport:
    differences: tuple[Difference, ...]
    ledger: Ledger

    @classmethod
    def measure(cls, fixtures: Iterable[Fixture], ledger: Ledger) -> CorpusReport:
        return cls(tuple(fixture.difference() for fixture in fixtures), ledger)

    def observations(self) -> frozenset[Observation]:
        return frozenset().union(*(difference.observations() for difference in self.differences))

    @property
    def exact(self) -> int:
        return sum(1 for difference in self.differences if difference.exact)

    def readme_block(self) -> str:
        total = len(self.differences)
        remaining = self.ledger.remaining()
        color = "brightgreen" if not remaining else "yellow"
        badge = (
            "![owlrl reference closures](https://img.shields.io/badge/"
            f"owlrl%20goldens-{self.exact}%2F{total}%20exact-{color}?style=flat)"
        )
        rows = "\n".join(
            f"| `{entry.kind.value}` | {entry.rule} | {entry.status.value} | "
            + ", ".join(f"`{name}`" for name in sorted(entry.fixtures))
            + " |"
            for entry in remaining
        )
        return (
            f"{README_START}\n{badge}\n\n"
            f"**{self.exact} of {total} reference fixtures match owlrl {pinned_owlrl()} exactly; "
            f"{len(remaining)} ledgered differences remain.**\n\n"
            "| Kind | Rule | Status | Fixtures |\n| --- | --- | --- | --- |\n"
            f"{rows}\n{README_END}"
        )


def pinned_owlrl() -> str:
    dependencies = tomllib.loads(GOLDEN_TOOLS.read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    (pin,) = (item for item in dependencies if item.startswith("owlrl=="))
    return pin.removeprefix("owlrl==")


README_START = "<!-- owlrl-divergence-ledger:start -->"
README_END = "<!-- owlrl-divergence-ledger:end -->"


def readme_section(text: str) -> str:
    start = text.index(README_START)
    end = text.index(README_END) + len(README_END)
    return text[start:end]


def write_readme(report: CorpusReport) -> None:
    text = README.read_text(encoding="utf-8")
    README.write_text(text.replace(readme_section(text), report.readme_block()), encoding="utf-8")


if __name__ == "__main__":
    write_readme(CorpusReport.measure(Fixture.corpus(), Ledger.load()))
