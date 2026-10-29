"""Test isolation for menkyo.

A real dōjō's identity may sit in ./dojo.toml and in the per-user folder, and
an unpinned run picks either up.  So, before menkyo is imported at all, HOME
and XDG_CONFIG_HOME are moved to a throwaway directory (menkyo.config computes
USER_CONFIG at import); and for every test the module constants that name
those files are pointed into the test's own tmp_path.  Subprocesses get the
same treatment through support.isolated_env(), and always pass -c.

Renders are real: the package draws with pypdfium2 and needs no program on
the host, so nothing is stood in for and nothing skips for want of a tool.
Tests marked `render` are the ones that render (seconds each).
"""

import os
import pwd
import shutil
import tempfile

# ---- before anything imports menkyo ------------------------------------------
REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir
_SESSION_HOME = tempfile.mkdtemp(prefix="menkyo-test-home-")
os.environ["HOME"] = _SESSION_HOME
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SESSION_HOME, ".config")

import pytest  # noqa: E402

import support  # noqa: E402
from menkyo import build_diploma, config as config_mod  # noqa: E402


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
