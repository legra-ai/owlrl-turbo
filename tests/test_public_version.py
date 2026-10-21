"""Public package versions follow the installed artifact's metadata."""

from importlib import metadata, reload

import pytest
from packaging.requirements import Requirement

import owlrl_turbo


def test_independently_versioned_artifact_reports_installed_version(tmp_path, monkeypatch):
    distribution = tmp_path / "owlrl_turbo-99.0.0.dist-info"
    distribution.mkdir()
    (distribution / "METADATA").write_text(
        "Metadata-Version: 2.3\nName: owlrl-turbo\nVersion: 99.0.0\n"
    )
    try:
        with monkeypatch.context() as context:
            context.syspath_prepend(str(tmp_path))
            assert metadata.version("owlrl-turbo") == "99.0.0"
            reload(owlrl_turbo)
            assert owlrl_turbo.__version__ == metadata.version("owlrl-turbo")
    finally:
        reload(owlrl_turbo)


@pytest.mark.parametrize(
    "package, next_minor", [("rdflib-turbo", "0.3.0"), ("pyshacl-turbo", "0.5.0")]
)
def test_companion_requirements_allow_coordinated_minor_releases(package, next_minor):
    requirements = [Requirement(value) for value in metadata.requires("owlrl-turbo")]
    companion = next(requirement for requirement in requirements if requirement.name == package)
    assert next_minor in companion.specifier
