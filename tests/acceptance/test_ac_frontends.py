"""AC-12: the desktop window and the web front end build on the package.

The web endpoints are exercised in tests/regression/test_web.py; here, the
two modules import the way they are run (`python src/gui.py`,
`uvicorn app:app --app-dir web`) and use menkyo's own modules.
"""

import subprocess
import sys

import pytest

import support


def _run(code, home, cwd):
    return subprocess.run([sys.executable, "-c", code], env=support.isolated_env(home),
                          cwd=str(cwd), capture_output=True, text=True, timeout=120)


def test_ac12_web_app_imports(home):
    pytest.importorskip("fastapi")
    r = _run("import sys; sys.path.insert(0, 'web'); import app; "
             "import menkyo.service as s; assert app.make_argv is s.make_argv; "
             "assert app.run_build is s.run_build; "
             "print(sorted(r.path for r in app.app.routes))", home, support.REPO)
    assert r.returncode == 0, r.stderr
    for route in ("/", "/api/state", "/api/settings", "/api/generate"):
        assert f"'{route}'" in r.stdout


def test_ac12_gui_imports(home):
    probe = _run("import tkinter", home, support.REPO)
    if probe.returncode != 0:
        pytest.skip("Tk is not available to this Python")
    # As `python src/gui.py` would: src/ is on sys.path, the window is not opened.
    r = _run("import sys; sys.path.insert(0, 'src'); import gui; "
             "import menkyo.service as s; assert gui.make_argv is s.make_argv; "
             "assert gui.run_build is s.run_build; print(gui.App.__name__)",
             home, support.REPO)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "App"


def test_ac12_no_flat_imports_left():
    """Nothing still imports the old top-level modules (config, paths, service ...)."""
    import re
    flat = re.compile(r"^\s*(import|from)\s+(config|paths|service|build_diploma|border|ink)\b",
                      re.M)
    for f in [support.SRC / "gui.py", support.REPO / "web" / "app.py",
              *support.PACKAGE.glob("*.py")]:
        assert not flat.search(f.read_text(encoding="utf-8")), f
