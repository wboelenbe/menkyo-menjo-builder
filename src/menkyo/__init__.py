"""Japanese dan-grade and menkyo certificates.

The command line (`menkyo`, or `python -m menkyo`) is the interface: other
programs run it with --json and read its events rather than importing the
modules, which keep their state in globals.  See build_diploma.py.
"""

import os
import tomllib
from importlib.metadata import PackageNotFoundError, version

from . import paths


def _version():
    # A checkout answers from pyproject.toml, which an editable install's
    # metadata may lag behind; an installed copy answers from its metadata.
    root = paths.checkout_root()
    if root:
        with open(os.path.join(root, "pyproject.toml"), "rb") as fh:
            return tomllib.load(fh)["project"]["version"]
    try:
        return version("menkyo")
    except PackageNotFoundError:
        return "unknown"


__version__ = _version()
