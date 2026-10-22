"""Exercise published native APIs at the dependency floor declared by the wheel."""

import subprocess
import sys
import tempfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
from wheel_install import install_wheel


def minimum_runtime(wheel):
    with ZipFile(wheel) as archive:
        members = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(members) != 1:
            raise ValueError("Expected exactly one wheel METADATA file")
        metadata = BytesParser().parsebytes(archive.read(members[0]))
    requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
    runtime = [value for value in requirements if canonicalize_name(value.name) == "rdflib-turbo"]
    if len(runtime) != 1 or runtime[0].marker is not None or runtime[0].url is not None:
        raise ValueError("Expected one unconditional registry runtime requirement")
    floors = [
        Version(item.version) for item in runtime[0].specifier if item.operator in {">=", "=="}
    ]
    if len(floors) != 1 or floors[0] not in runtime[0].specifier:
        raise ValueError("Expected one concrete inclusive runtime minimum")
    return str(floors[0])


def test_minimum_runtime(wheel):
    minimum = minimum_runtime(wheel)
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory) / "project"
        subprocess.run(
            [
                "uv",
                "init",
                "--bare",
                "--no-workspace",
                "--vcs",
                "none",
                "--python",
                python,
                str(project),
            ],
            check=True,
        )
        install_wheel(
            project, wheel, test_extra=False, runtime_requirement=f"rdflib-turbo=={minimum}"
        )
        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(project),
                "--locked",
                "--no-sync",
                "python",
                "-I",
                "-c",
                PROBE,
                minimum,
            ],
            cwd=directory,
            check=True,
        )


PROBE = """import sys
from importlib.metadata import version
assert version("rdflib-turbo") == sys.argv[1]
from rdflib import Graph, Namespace, RDF, RDFS
from owlrl_turbo import DeductiveClosure, RDFS_Semantics, expand
import rdflib_turbo
terms = Namespace("urn:minimum:")
triples = [(terms.s, RDF.type, terms.C), (terms.C, RDFS.subClassOf, terms.D)]
legacy = Graph()
for triple in triples:
    legacy.add(triple)
DeductiveClosure(RDFS_Semantics, axiomatic_triples=True, datatype_axioms=True).expand(legacy)
assert (terms.s, RDF.type, terms.D) in legacy
native = rdflib_turbo.Graph()
for triple in triples:
    native.add(triple)
result = expand(native, inference="rdfs")
assert result is not native
assert (terms.s, RDF.type, terms.D) in result
assert (terms.s, RDF.type, terms.D) not in native
"""


if __name__ == "__main__":
    wheels = list((Path(__file__).resolve().parents[1] / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one built wheel")
    test_minimum_runtime(wheels[0])
