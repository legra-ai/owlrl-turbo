"""Install and test built wheels in isolated Python 3.11 and 3.14 environments."""

import os
import subprocess
import tempfile
from pathlib import Path

from wheel_install import build_runtime_wheel, install_wheel

root = Path(__file__).resolve().parents[1]
wheels = list((root / "dist").glob("*.whl"))
if len(wheels) != 1:
    raise ValueError("Expected exactly one built wheel")
with tempfile.TemporaryDirectory() as runtime_directory:
    runtime = os.environ.get("OWLRL_TEST_RUNTIME_SOURCE")
    runtime_wheel = (
        build_runtime_wheel(runtime, "3.11", Path(runtime_directory) / "provider-wheel")
        if runtime is not None
        else None
    )
    if runtime_wheel is not None and runtime_wheel.name.rsplit("-", 3)[-2] != "abi3":
        raise ValueError("Shared interpreter acceptance requires an ABI3 provider wheel")
    for version in ("3.11", "3.14"):
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
                    version,
                    str(project),
                ],
                check=True,
            )
            subprocess.run(["uv", "python", "pin", "--project", str(project), version], check=True)
            install_wheel(project, wheels[0], runtime_wheel=runtime_wheel)
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--project",
                    str(project),
                    "--locked",
                    "pytest",
                    str(root / "tests"),
                    "-q",
                    "--import-mode=importlib",
                    "--cov=owlrl_turbo",
                    "--cov-branch",
                    "--cov-fail-under=100",
                ],
                cwd=directory,
                check=True,
            )
