"""Where things live: bundled resources, the user's files, external tools.

The same code has to run four ways -- from a checkout, installed as a wheel
(pip, uv, Homebrew), and frozen inside a .app -- and a Finder-launched app
inherits none of the shell's PATH.  Everything that depends on which of those
it is happens here, so the rest of the code can ask for a path and not care.
"""

import os
import shutil
import sys
import tomllib

APP_NAME = "Menkyo"

# The package directory.  fonts/ and example.toml travel inside it, so they
# sit beside this file however the package was installed -- PyInstaller too,
# which places the package's data files under sys._MEIPASS/menkyo.
HERE = os.path.dirname(os.path.abspath(__file__))


def checkout_root():
    """The repository root when running from a checkout, else None.

    Only a checkout has a dojo.toml beside the code and a ./build to write
    into; an installed or frozen copy must never look next to itself.  The
    pyproject.toml has to be this project's own: a copy vendored inside some
    other project sits under that project's pyproject.toml, and is no checkout.
    """
    if getattr(sys, "frozen", False):
        return None
    root = os.path.normpath(os.path.join(HERE, "..", ".."))
    try:
        with open(os.path.join(root, "pyproject.toml"), "rb") as fh:
            project = tomllib.load(fh).get("project", {})
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return root if project.get("name") == "menkyo" else None


def resource(*parts):
    """A file shipped inside the package: fonts, the example config."""
    return os.path.join(HERE, *parts)


def user_data_dir():
    """Per-user, writable: the dōjō's own configuration lives here."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, APP_NAME)


def default_output_dir():
    """Where certificates go unless told otherwise.

    A checkout keeps its historical ./build; anything installed or frozen
    writes where a non-technical user will look for it.
    """
    root = checkout_root()
    if root:
        return os.path.join(root, "build")
    return os.path.join(os.path.expanduser("~/Documents"), APP_NAME)


# Where Homebrew, the Inkscape disk image and MacPorts put things.  A GUI app
# started from Finder sees only /usr/bin:/bin:/usr/sbin:/sbin.
_EXTRA_BIN = [
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/opt/local/bin",
    "/Applications/Inkscape.app/Contents/MacOS",
]

_INSTALL_HINT = {
    "inkscape": "Inkscape (https://inkscape.org/release/, or: brew install --cask inkscape)",
    "gs": "Ghostscript (brew install ghostscript)",
}


def find_tool(name):
    """Absolute path of an external program, or None."""
    found = shutil.which(name)
    if found:
        return found
    for d in _EXTRA_BIN:
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def require_tool(name):
    """Like find_tool, but a missing program ends the run with instructions."""
    found = find_tool(name)
    if not found:
        raise SystemExit(
            f"{name} was not found. Please install {_INSTALL_HINT.get(name, name)} "
            f"and try again.")
    return found


def tool_env(base=None):
    """An environment whose PATH can see the tools find_tool would."""
    env = dict(base if base is not None else os.environ)
    parts = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
    env["PATH"] = os.pathsep.join(parts + [d for d in _EXTRA_BIN if d not in parts])
    return env


def system_font_dirs():
    """Font directories fontconfig should see on top of the vendored font."""
    dirs = ["/System/Library/Fonts", "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts")]
    return [d for d in dirs if os.path.isdir(d)]
