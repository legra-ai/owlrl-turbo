"""Resolve and sync the exact release wheel in an isolated native uv project."""

import subprocess
from pathlib import Path


def install_wheel(project, wheel, *, test_extra=True, runtime_wheel=None, runtime_requirement=None):
    if runtime_wheel is not None and runtime_requirement is not None:
        raise ValueError("Select a runtime wheel or registry requirement, not both")
    # A just-published runtime must invalidate uv's cached empty index response.
    arguments = ["uv", "add", "--project", str(project), "--no-sync", "--refresh"]
    if test_extra:
        arguments.extend(["--extra", "test"])
    arguments.append(str(wheel))
    if runtime_wheel is not None:
        arguments.append(str(runtime_wheel))
    if runtime_requirement is not None:
        arguments.append(runtime_requirement)
    subprocess.run(arguments, cwd=project, check=True)
    subprocess.run(["uv", "sync", "--project", str(project), "--locked"], cwd=project, check=True)


def build_runtime_wheel(source, version, output):
    """Build the pinned provider for the interpreter that will install it."""
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--python",
            version,
            "--out-dir",
            str(output),
            "-C",
            "maturin.build-args=--locked",
            str(source),
        ],
        cwd=source,
        check=True,
    )
    wheels = list(output.glob("rdflib_turbo-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one built provider wheel")
    return wheels[0]
