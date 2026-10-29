"""Helpers shared by the tests and by tests/regression/make_golden.py.

Nothing here reads a real dōjō's configuration: every run is given `-c` with
the shipped example or a config the test wrote, and HOME / XDG_CONFIG_HOME
point at a throwaway directory.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PACKAGE = SRC / "menkyo"
EXAMPLE = PACKAGE / "example.toml"
TESTS = REPO / "tests"
DATA = TESTS / "data"

# The baseline the goldens are generated from: 823af58, the last commit before
# plain-white.  Its overlay, overlay-flat and proof output is what the current
# code must still write, byte for byte.  (The packaging item's baseline was
# d96c08d; 823af58 was itself checked against it.)
BASELINE_REF = "823af58"

PERSONAL = ("dojo.toml", "crest", "ref")


def isolated_env(home, path_prepend=(), path=None, **extra):
    """os.environ with HOME and XDG_CONFIG_HOME moved to `home`.

    `path` replaces PATH outright; `path_prepend` puts directories in front of
    the inherited one.
    """
    home = Path(home)
    (home / ".config").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env.pop("PYTHONPATH", None)
    base = path if path is not None else env.get("PATH", "")
    env["PATH"] = os.pathsep.join([str(p) for p in path_prepend] + ([base] if base else []))
    env.update({k: str(v) for k, v in extra.items()})
    return env


def run_menkyo(args, env, cwd, exe=None, timeout=600, **kw):
    """Run the CLI in a subprocess; `exe` defaults to `python -m menkyo`."""
    cmd = list(exe) if exe else [sys.executable, "-m", "menkyo"]
    return subprocess.run(cmd + [str(a) for a in args], env=env, cwd=str(cwd),
                          capture_output=True, text=True, timeout=timeout, **kw)


def events(stdout):
    """Every stdout line parsed as JSON; fails on a line that is not an object."""
    out = []
    for i, line in enumerate(stdout.splitlines()):
        obj = json.loads(line)          # raises on a non-JSON line
        assert isinstance(obj, dict) and "event" in obj, f"line {i}: {line!r}"
        out.append(obj)
    return out


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def project_version():
    import tomllib
    with open(REPO / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def copy_package(dest):
    """A copy of src/menkyo at `dest`/menkyo, without caches."""
    dest = Path(dest)
    shutil.copytree(PACKAGE, dest / "menkyo",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest / "menkyo"
