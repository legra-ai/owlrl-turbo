"""The class facade is exercised with current companion releases."""

from importlib.metadata import requires

from packaging.requirements import Requirement


def test_companion_extra_accepts_current_public_release():
    companion = next(
        Requirement(item)
        for item in requires("owlrl-turbo")
        if Requirement(item).name == "pyshacl-turbo"
    )
    assert companion.specifier.contains("0.4.1")
    assert not companion.specifier.contains("0.2.10")
