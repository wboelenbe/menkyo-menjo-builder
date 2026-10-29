"""Test isolation for menkyo.

A real dōjō's identity may sit in ./dojo.toml and in the per-user folder, and
an unpinned run picks either up.  So, before menkyo is imported at all, HOME
and XDG_CONFIG_HOME are moved to a throwaway directory (menkyo.config computes
USER_CONFIG at import); and for every test the module constants that name
those files are pointed into the test's own tmp_path.  Subprocesses get the
same treatment through support.isolated_env(), and always pass -c.
"""

import os
import pwd
import shutil
import tempfile
from pathlib import Path

# ---- before anything imports menkyo ------------------------------------------
REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir
_SESSION_HOME = tempfile.mkdtemp(prefix="menkyo-test-home-")
os.environ["HOME"] = _SESSION_HOME
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SESSION_HOME, ".config")

import pytest  # noqa: E402

import support  # noqa: E402
from menkyo import build_diploma, config as config_mod, paths  # noqa: E402

REQUIRE_RENDER = os.environ.get("REQUIRE_RENDER") == "1"


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_SESSION_HOME, ignore_errors=True)


def _under(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


@pytest.fixture(autouse=True)
def isolate_user_files(tmp_path, monkeypatch):
    """No test can reach the real per-user or repository-root dojo.toml.

    Yields the test's fake HOME.
    """
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))

    user_config = str(home / "user-data" / "dojo.toml")
    monkeypatch.setattr(config_mod, "USER_CONFIG", user_config)
    monkeypatch.setattr(config_mod, "LOCAL_CONFIG", None)
    # save()'s default was bound at import; rebind it too.
    monkeypatch.setattr(config_mod.save, "__defaults__", (user_config,))
    # A forgotten --out must not land in the checkout's build/.
    monkeypatch.setattr(build_diploma, "BUILD", str(tmp_path / "default-build"))

    assert not _under(config_mod.USER_CONFIG, REAL_HOME)
    assert config_mod.default_path() == config_mod.EXAMPLE_CONFIG
    yield home


@pytest.fixture
def home(isolate_user_files):
    return isolate_user_files


class FakeTools:
    """Stand-in inkscape on PATH, its call log, and the captured text layers."""

    def __init__(self, root, tools=("inkscape",)):
        self.bin = support.make_fake_bin(root / "fakebin", tools)
        self.log = root / "fake-tools.jsonl"
        self.capture = root / "captured"

    def env(self, home, **extra):
        """Environment for a subprocess: fakes first, nothing else on PATH but
        the system directories (so a real Inkscape is never picked up)."""
        return support.isolated_env(
            home, path_prepend=[self.bin], path="/usr/bin:/bin",
            FAKE_TOOL_LOG=self.log, FAKE_CAPTURE_DIR=self.capture, **extra)

    def calls(self, tool=None):
        return [c for c in support.read_log(self.log)
                if tool is None or c["tool"] == tool]


@pytest.fixture
def fake_tools(tmp_path, monkeypatch):
    """Fakes for in-process runs too: PATH holds only them, and the extra
    places paths.find_tool() searches (Homebrew etc.) are switched off."""
    ft = FakeTools(tmp_path)
    monkeypatch.setenv("PATH", f"{ft.bin}{os.pathsep}/usr/bin:/bin")
    monkeypatch.setenv("FAKE_TOOL_LOG", str(ft.log))
    monkeypatch.setenv("FAKE_CAPTURE_DIR", str(ft.capture))
    monkeypatch.setattr(paths, "_EXTRA_BIN", [])
    return ft


@pytest.fixture
def no_tools(tmp_path, monkeypatch):
    """Inkscape cannot be found, in-process."""
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(paths, "_EXTRA_BIN", [])
    return empty


@pytest.fixture(scope="session")
def inkscape():
    """The real Inkscape, for `render` tests.  Missing: skip, or fail under
    REQUIRE_RENDER=1 (the Docker image and CI), so a broken image cannot
    pass by skipping everything."""
    found = support.find_inkscape()
    if not found:
        if REQUIRE_RENDER:
            pytest.fail("REQUIRE_RENDER=1 but Inkscape was not found")
        pytest.skip("Inkscape not installed (set REQUIRE_RENDER=1 to make this fail)")
    return found


def require_program(name):
    """A helper program (pdffonts, pdfinfo) a render test needs."""
    found = shutil.which(name)
    if not found:
        if REQUIRE_RENDER:
            pytest.fail(f"REQUIRE_RENDER=1 but {name} was not found")
        pytest.skip(f"{name} not installed")
    return found


@pytest.fixture(scope="session")
def session_home(tmp_path_factory):
    h = tmp_path_factory.mktemp("session-home")
    (h / ".config").mkdir()
    return h


@pytest.fixture(scope="session")
def dist(tmp_path_factory):
    """`uv build` of the checkout: the sdist, and the wheel built from it."""
    uv = shutil.which("uv")
    if not uv:
        pytest.skip("uv not available to build the wheel")
    out = tmp_path_factory.mktemp("dist")
    import subprocess
    r = subprocess.run([uv, "build", "--out-dir", str(out), str(support.REPO)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    wheels, sdists = list(out.glob("*.whl")), list(out.glob("*.tar.gz"))
    assert len(wheels) == 1 and len(sdists) == 1, list(out.iterdir())
    return {"wheel": wheels[0], "sdist": sdists[0], "dir": out}


@pytest.fixture(scope="session")
def installed(dist, tmp_path_factory):
    """The wheel installed into a fresh virtualenv, outside the checkout."""
    import subprocess
    import sys
    uv = shutil.which("uv")
    venv = tmp_path_factory.mktemp("venv") / "v"
    r = subprocess.run([uv, "venv", "--python", sys.executable, str(venv)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    py = venv / "bin" / "python"
    r = subprocess.run([uv, "pip", "install", "--python", str(py), str(dist["wheel"])],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    return {"venv": venv, "python": py, "menkyo": venv / "bin" / "menkyo"}
