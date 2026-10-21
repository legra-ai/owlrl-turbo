"""Public package versions follow the installed artifact's metadata."""

from importlib import metadata, reload

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
