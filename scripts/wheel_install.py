"""Resolve and sync the exact release wheel in an isolated native uv project."""

import subprocess


def install_wheel(project, wheel, *, test_extra=True):
    # A just-published runtime must invalidate uv's cached empty index response.
    arguments = ["uv", "add", "--project", str(project), "--no-sync", "--refresh"]
    if test_extra:
        arguments.extend(["--extra", "test"])
    arguments.append(str(wheel))
    subprocess.run(arguments, check=True)
    subprocess.run(["uv", "sync", "--project", str(project), "--locked"], check=True)
