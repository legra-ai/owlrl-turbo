"""Make the shared owlrl reference helpers importable under --import-mode=importlib."""

import sys
from pathlib import Path

TESTS = str(Path(__file__).resolve().parent)
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)
