"""Packaging tools are explicit locked project dependencies."""

import tomllib
from pathlib import Path

import yaml


def test_release_twine_uses_only_the_locked_packaging_group():
    root = Path(__file__).resolve().parents[1]
    manifest = tomllib.loads((root / "pyproject.toml").read_text())
    assert manifest["dependency-groups"]["packaging"] == ["twine==7.0.0"]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text())
    commands = [
        step.get("run", "") for job in workflow["jobs"].values() for step in job.get("steps", [])
    ]
    checks = [command for command in commands if "twine check" in command]
    assert checks
    assert all(
        "uv --project tools/packaging run --locked --only-group packaging twine check --strict"
        in command
        for command in checks
    )
    assert not any("uv tool run" in command for command in commands)
