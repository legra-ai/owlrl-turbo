"""The wheel's actual runtime floor must be explicit and exercised independently."""

import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture
def gate(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "minimum_runtime_gate", scripts / "test_minimum_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata_wheel(tmp_path, requirements):
    path = tmp_path / "owlrl_turbo-0.0.0-py3-none-any.whl"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "owlrl_turbo-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: owlrl-turbo\nVersion: 0.0.0\n"
            + "".join(f"Requires-Dist: {value}\n" for value in requirements),
        )
    return path


def test_minimum_comes_from_the_packaged_requirement(gate, tmp_path):
    wheel = metadata_wheel(tmp_path, ["rdflib>=7", "RDFLIB_turbo>=0.2.0-alpha.8"])
    assert gate.minimum_runtime(wheel) == "0.2.0a8"


@pytest.mark.parametrize(
    "requirements",
    [
        [],
        ["rdflib-turbo>0.2.0a5"],
        ["rdflib-turbo>=0.2.0a5; python_version >= '3.13'"],
        ["rdflib-turbo @ https://example.invalid/runtime.whl"],
        ["rdflib-turbo>=0.2.0a5", "rdflib-turbo>=0.2.0a6"],
        ["rdflib-turbo>=0.2.0a5,!=0.2.0a5"],
    ],
)
def test_ambiguous_runtime_minimum_fails_before_installation(gate, tmp_path, requirements):
    with pytest.raises(ValueError):
        gate.minimum_runtime(metadata_wheel(tmp_path, requirements))


def test_candidate_and_minimum_cannot_be_selected_together(gate, tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "minimum_wheel_install", Path(gate.__file__).with_name("wheel_install.py")
    )
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)

    def unexpected(*args, **kwargs):
        raise AssertionError("Ambiguous runtime selection reached an installer")

    monkeypatch.setattr(installer.subprocess, "run", unexpected)
    with pytest.raises(ValueError, match="Select a runtime"):
        installer.install_wheel(
            tmp_path,
            tmp_path / "consumer.whl",
            runtime_wheel=tmp_path / "candidate.whl",
            runtime_requirement="rdflib-turbo==0.2.0a5",
        )
