"""Install and test built wheels in isolated Python 3.11 and 3.14 environments."""

import os
import subprocess
import tempfile
from pathlib import Path

from wheel_install import install_wheel

root = Path(__file__).resolve().parents[1]
wheels = list((root / "dist").glob("*.whl"))
if len(wheels) != 1:
    raise ValueError("Expected exactly one built wheel")
for version in ("3.11", "3.14"):
    with tempfile.TemporaryDirectory() as directory:
        environment = Path(directory) / "venv"
        subprocess.run(["uv", "venv", "--python", version, str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        install_wheel(python, wheels[0])
        subprocess.run(
            [
                str(python),
                "-m",
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
