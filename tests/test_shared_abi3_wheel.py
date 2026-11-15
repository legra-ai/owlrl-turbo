"""Interpreter acceptance must reuse the exact same ABI3 provider archive."""

import runpy
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("abi", ["abi3", "cp311"])
def test_both_interpreters_install_one_identical_provider_wheel(tmp_path, monkeypatch, abi):
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "scripts/test_wheel.py"
    script.parent.mkdir()
    shutil.copyfile(root / "scripts/test_wheel.py", script)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "owlrl_turbo-0.2.0a2-py3-none-any.whl").touch()
    source = tmp_path / "provider"
    source.mkdir()
    monkeypatch.setenv("OWLRL_TEST_RUNTIME_SOURCE", str(source))
    builds = []
    installs = []
    interpreters = []

    def build(provider, version, output):
        builds.append((provider, version))
        output.mkdir(parents=True)
        wheel = output / f"rdflib_turbo-0.2.0a39-cp311-{abi}-platform.whl"
        wheel.write_bytes(b"original ABI3 archive")
        return wheel

    def install(project, facade, *, runtime_wheel):
        assert project.is_dir()
        installs.append((runtime_wheel, runtime_wheel.read_bytes()))

    def run(command, *, check, cwd=None):
        assert check is True
        if command[1] == "init":
            Path(command[-1]).mkdir()
        if command[1:3] == ["python", "pin"]:
            interpreters.append(command[-1])

    monkeypatch.setitem(
        sys.modules,
        "wheel_install",
        SimpleNamespace(build_runtime_wheel=build, install_wheel=install),
    )
    monkeypatch.setattr("subprocess.run", run)
    if abi != "abi3":
        with pytest.raises(ValueError, match="ABI3"):
            runpy.run_path(str(script))
        assert not installs
        return
    runpy.run_path(str(script))
    assert builds == [(str(source), "3.11")]
    assert interpreters == ["3.11", "3.14"]
    assert len(installs) == 2
    assert installs[0] == installs[1]
