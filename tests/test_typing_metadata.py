"""The installed facade advertises its typed API and current companion tests."""

import inspect
from importlib.metadata import requires
from importlib.resources import files
from pathlib import Path
from typing import get_overloads

from packaging.requirements import Requirement

from owlrl_turbo import expand


def test_installed_package_advertises_inline_types():
    assert files("owlrl_turbo").joinpath("py.typed").is_file()
    assert inspect.signature(expand).return_annotation is not inspect.Signature.empty
    assert len(get_overloads(expand)) == 3


def test_test_extra_runs_current_companion_release():
    import tomllib

    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    requirement = next(
        Requirement(item)
        for item in project["optional-dependencies"]["test"]
        if Requirement(item).name == "pyshacl-turbo"
    )
    assert requirement.specifier.contains("0.4.1")
    assert not requirement.specifier.contains("0.2.7")


def test_runtime_requirement_excludes_releases_without_native_delta():
    requirement = next(
        Requirement(item)
        for item in requires("owlrl-turbo")
        if Requirement(item).name == "rdflib-turbo"
    )
    assert requirement.specifier.contains("0.2.0a5", prereleases=True)
    assert not requirement.specifier.contains("0.2.0a4", prereleases=True)
