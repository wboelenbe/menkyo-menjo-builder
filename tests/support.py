"""Helpers shared by the tests and by tests/regression/make_golden.py.

Nothing here reads a real dōjō's configuration: every run is given `-c` with
the shipped example or a config the test wrote, and HOME / XDG_CONFIG_HOME
point at a throwaway directory.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
PACKAGE = SRC / "menkyo"
EXAMPLE = PACKAGE / "example.toml"
TESTS = REPO / "tests"
FAKE_TOOL = TESTS / "fakes" / "fake_tool.py"
DATA = TESTS / "data"

# The baseline the packaging work must not change: the last commit before it.
BASELINE_REF = "d96c08d"

PERSONAL = ("dojo.toml", "crest", "ref")


def make_fake_bin(bin_dir, tools=("inkscape", "gs"), python=sys.executable):
    """Write shell wrappers named after `tools` that run tests/fakes/fake_tool.py."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    for tool in tools:
        p = bin_dir / tool
        p.write_text(f'#!/bin/sh\nexec "{python}" "{FAKE_TOOL}" {tool} "$@"\n')
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


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


def read_log(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


_BORDER_START = '<defs><clipPath id="bd"'


def normalise_svg(text):
    """The SVG with the 800 kB generated border replaced by a one-line hash.

    Only for storing and diffing goldens; equality is always checked on the
    raw bytes.  The border runs from its <defs> to the closing tag of its
    square-capped rules group.
    """
    start = text.find(_BORDER_START)
    if start < 0:
        return text
    rules = text.find('stroke-linecap="square">', start)
    end = text.find("</g>", rules) + len("</g>")
    block = text[start:end]
    colour = re.search(r'stroke="(#[0-9a-fA-F]{6})"', block)
    return (text[:start]
            + f"<!-- border colour={colour.group(1) if colour else '?'} "
              f"sha256={sha256(block)} -->"
            + text[end:])


def find_inkscape():
    """Inkscape as the generator would find it, or None."""
    from menkyo import paths
    return paths.find_tool("inkscape")


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
