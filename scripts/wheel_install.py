"""Install a built wheel and its declared dependencies for release verification."""

import subprocess


def install_wheel(python, wheel, *, test_extra=True):
    requirement = str(wheel) + ("[test]" if test_extra else "")
    # Release checks must revalidate index metadata that can predate a new dependency.
    subprocess.run(
        ["uv", "pip", "install", "--refresh", "--python", str(python), requirement],
        check=True,
    )
