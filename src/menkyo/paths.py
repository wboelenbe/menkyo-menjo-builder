"""Where things live: bundled resources and the user's files.

The same code runs from a checkout and installed as a wheel (pip, uv).
Everything that depends on which of those it is happens here, so the rest of
the code can ask for a path and not care.  No external program is needed,
so none is looked for.
"""

import os
import sys
import tomllib

APP_NAME = "Menkyo"

# The package directory.  fonts/ and example.toml travel inside it, so they
# sit beside this file however the package was installed.
HERE = os.path.dirname(os.path.abspath(__file__))


def checkout_root():
    """The repository root when running from a checkout, else None.

    Only a checkout has a dojo.toml beside the code and a ./build to write
    into; an installed copy must never look next to itself.  The
    pyproject.toml has to be this project's own: a copy vendored inside some
    other project sits under that project's pyproject.toml, and is no checkout.
    """
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

    A checkout keeps its historical ./build; an installed copy writes where
    a non-technical user will look for it.
    """
    root = checkout_root()
    if root:
        return os.path.join(root, "build")
    return os.path.join(os.path.expanduser("~/Documents"), APP_NAME)
