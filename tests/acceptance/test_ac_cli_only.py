"""cli-only: no Mac app, no web front end, no deploy -- the command is the product.

See docs/work/cli-only/acceptance.md.  The AC numbers here are that item's
(AC-1 .. AC-14), not the packaging item's.  This file is the one place that
spells out the words the rest of the repository may no longer contain, so it
excludes itself from that scan.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

import support

THIS = Path(__file__).resolve()
BEFORE = "90e5799"          # HEAD when the item was planned

REMOVED_FILES = ["src/gui.py", "src/menkyo/service.py", ".dockerignore"]
REMOVED_DIRS = ["packaging", "web", "deploy"]
REMOVED_TESTS = ["tests/regression/test_web.py", "tests/regression/test_service.py",
                 "tests/acceptance/test_ac_frontends.py"]

# Machine-local leftovers of the removed app.  Never in the repository; the
# item does not delete them (scope: out), but they must not become untracked
# files once their .gitignore lines go.
LEFTOVERS = ["build-app", "packaging", "web", "deploy"]


# ----------------------------------------------------------------- helpers ----
def _git(*args):
    if not shutil.which("git") or not (support.REPO / ".git").exists():
        return None
    r = subprocess.run(["git", "-C", str(support.REPO), *args],
                       capture_output=True, text=True)
    return r if r.returncode == 0 else None


def needs_git(*args):
    r = _git(*args)
    if r is None:
        pytest.skip("not a git checkout (the Docker test image has no .git)")
    return r.stdout


_WALK_SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist",
              "build-app", "crest", "ref"}


def repo_files():
    """Every file the repository holds or would pick up, relative to REPO:
    tracked and untracked-but-not-ignored, present on disk.  Without git
    (the Docker image), a walk that skips what .gitignore would."""
    r = _git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if r is not None:
        names = [n for n in r.stdout.split("\0") if n]
        return sorted({n for n in names if (support.REPO / n).is_file()})
    out = []
    for root, dirs, files in os.walk(support.REPO):
        dirs[:] = [d for d in dirs if d not in _WALK_SKIP]
        for f in files:
            if f == "dojo.toml" or f.endswith(".pyc"):
                continue
            out.append(str(Path(root, f).relative_to(support.REPO)))
    return sorted(out)


def text_of(rel):
    try:
        return (support.REPO / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None                     # binary: fonts, images


# ------------------------------------------------------------------ AC-1 ----
def test_ac1_removed_paths_are_gone():
    files = repo_files()
    for f in REMOVED_FILES + REMOVED_TESTS:
        assert f not in files, f
        assert not (support.REPO / f).exists(), f
    for d in REMOVED_DIRS:
        left = [f for f in files if f.startswith(d + "/")]
        assert left == [], left


# ------------------------------------------------------------------ AC-2 ----
# What may no longer be mentioned.  Case-insensitive unless (?-i:...).
# Deliberately allowed: `uv ... --frozen` (a uv flag), Inkscape.app and the
# Homebrew *tool* directories paths.find_tool() searches (see open question 2).
FORBIDDEN = [
    r"gui\.py", r"menkyo-gui", r"(?-i:\bTk\b)", r"\btkinter\b", r"python-tk",
    r"pyinstaller", r"_MEIPASS", r"(?<!-)\bfrozen\b",
    r"\.dmg\b", r"Menkyo\.app", r"(?<!\w)\.app\b", r"build_app", r"build-app",
    r"entitlements", r"notari[sz]", r"notarytool", r"codesign",
    r"desktop (app|window)", r"\bmac(os)? app\b",
    r"packaging/homebrew", r"menkyo\.rb", r"<tap>", r"brew tap",
    r"(?<![\w/.-])packaging/", r"(?<![\w/.-])web/", r"(?<![\w/.-])deploy/",
    r"\bcaddy", r"\bfastapi\b", r"\buvicorn\b", r"\bhttpx\b", r"\bstarlette\b",
    r"service\.py", r"menkyo\.service", r"\bimport service\b", r"from \.service\b",
    r"from \. import [\w, ]*\bservice\b",
    r"\bmake_argv\b", r"\brun_build\b", r"\bFormError\b",
    # no release flow (AC-13, AC-14)
    r"github releases?\b", r"releases/download", r"making a release",
]
SCAN_EXCLUDE_FILES = {"DECISIONS.md", str(THIS.relative_to(support.REPO))}
SCAN_EXCLUDE_DIRS = ("docs/work/", "tests/regression/golden/")


def test_ac2_no_references_left():
    pattern = re.compile("|".join(f"(?:{p})" for p in FORBIDDEN), re.I)
    hits = []
    for rel in repo_files():
        if rel in SCAN_EXCLUDE_FILES or rel.startswith(SCAN_EXCLUDE_DIRS):
            continue
        text = text_of(rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if m:
                hits.append(f"{rel}:{n}: {m.group(0)!r} in {line.strip()[:100]!r}")
    assert hits == [], "\n" + "\n".join(hits)


# ------------------------------------------------------------------ AC-3 ----
PROBE = r"""
import json, sys
sys.frozen = True                       # what PyInstaller used to set
sys._MEIPASS = "/nonexistent-bundle"
sys.path.insert(0, sys.argv[1])
from menkyo import paths, config
print(json.dumps({
    "checkout_root": paths.checkout_root(),
    "default_output_dir": paths.default_output_dir(),
    "fonts": paths.resource("fonts"),
    "local_config": config.LOCAL_CONFIG,
}))
"""


def test_ac3_frozen_flag_no_longer_matters(tmp_path):
    """A checkout stays a checkout even if sys.frozen is set: paths.py has no
    frozen-app branch any more."""
    r = subprocess.run([sys.executable, "-I", "-c", PROBE, str(support.SRC)],
                       env=support.isolated_env(tmp_path), cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got["checkout_root"] == str(support.REPO)
    assert got["default_output_dir"] == str(support.REPO / "build")
    assert got["local_config"] == str(support.REPO / "dojo.toml")
    assert got["fonts"] == str(support.PACKAGE / "fonts")


def test_ac3_paths_api_kept():
    from menkyo import paths
    for name in ("checkout_root", "resource", "user_data_dir", "default_output_dir",
                 "find_tool", "require_tool", "tool_env", "system_font_dirs"):
        assert callable(getattr(paths, name)), name
    src = (support.PACKAGE / "paths.py").read_text(encoding="utf-8")
    assert "sys.frozen" not in src and '"frozen"' not in src and "_MEIPASS" not in src


# ------------------------------------------------------------------ AC-4 ----
def _package_files():
    """src/menkyo as the wheel should ship it: every file but caches."""
    out = []
    for p in support.PACKAGE.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            out.append("menkyo/" + p.relative_to(support.PACKAGE).as_posix())
    return sorted(out)


def test_ac4_package_has_no_service_module():
    assert "menkyo/service.py" not in _package_files()
    with pytest.raises(ModuleNotFoundError):
        __import__("menkyo.service")


@pytest.mark.slow
def test_ac4_wheel_is_exactly_the_package(dist):
    with zipfile.ZipFile(dist["wheel"]) as z:
        payload = sorted(n for n in z.namelist() if ".dist-info/" not in n)
    assert payload == _package_files()
    assert "menkyo/service.py" not in payload


@pytest.mark.slow
def test_ac4_sdist_has_no_removed_paths(dist):
    with tarfile.open(dist["sdist"]) as t:
        names = [n.split("/", 1)[1] for n in t.getnames() if "/" in n]
    assert "src/menkyo/service.py" not in names and "src/gui.py" not in names
    assert not [n for n in names if n.split("/")[0] in REMOVED_DIRS]


# ------------------------------------------------------------------ AC-5 ----
def _pyproject():
    with open(support.REPO / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)


def test_ac5_dev_group_is_pytest_only():
    dev = _pyproject()["dependency-groups"]["dev"]
    names = {re.split(r"[<>=!~\[ ;]", d, maxsplit=1)[0].lower() for d in dev}
    assert names == {"pytest"}, dev
    warnings = _pyproject()["tool"]["pytest"]["ini_options"].get("filterwarnings", [])
    assert not [w for w in warnings if "httpx" in w or "starlette" in w], warnings


def test_ac5_runtime_dependencies_unchanged():
    deps = _pyproject()["project"]["dependencies"]
    assert deps == ["pillow>=9.0", "numpy>=1.22", "scipy>=1.8"]
    assert _pyproject()["project"]["scripts"] == {"menkyo": "menkyo.build_diploma:cli"}


def test_ac5_lockfile_has_no_web_packages():
    with open(support.REPO / "uv.lock", "rb") as fh:
        lock = tomllib.load(fh)
    names = {p["name"] for p in lock.get("package", [])}
    assert not names & {"fastapi", "httpx", "starlette", "uvicorn"}, names
    me = next(p for p in lock["package"] if p["name"] == "menkyo")
    dev = {d["name"] for d in me.get("dev-dependencies", {}).get("dev", [])}
    assert dev == {"pytest"}, dev


# ------------------------------------------------------------------ AC-6 ----
def _ignore_entries(path):
    return {l.strip().strip("/") for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")}


def test_ac6_gitignore_cleaned_up():
    entries = _ignore_entries(support.REPO / ".gitignore")
    for gone in ("build-app", "packaging/.venv", "deploy/.env"):
        assert gone not in entries, gone
    for kept in ("build", "dojo.toml", "crest", "ref", "dist", "__pycache__", "*.pyc"):
        assert kept in entries, kept


def test_ac6_test_image_ignore_cleaned_up():
    entries = _ignore_entries(support.TESTS / "docker" / "Dockerfile.dockerignore")
    for gone in ("build-app", "packaging/.venv", "deploy/.env"):
        assert gone not in entries, gone
    for kept in ("dojo.toml", "**/dojo.toml", "crest", "ref", "build", "dist",
                 ".venv", ".git"):
        assert kept in entries, kept


def test_ac6_no_leftovers_become_untracked():
    """Once their ignore lines go, local leftovers of the app (build-app/,
    packaging/.venv/ ...) must not show up as files to commit."""
    out = needs_git("ls-files", "--others", "--exclude-standard", "--directory")
    stray = [l for l in out.splitlines()
             if l.split("/")[0] in LEFTOVERS]
    assert stray == [], stray


# ------------------------------------------------------------------ AC-7 ----
def _help(src_dir, home):
    """`menkyo --help` from the checkout around src_dir, run from its root
    (the help names the configuration relative to the cwd)."""
    root = Path(os.path.realpath(src_dir)).parent
    # Wide enough that no line wraps, so the checkout path can be normalised.
    env = support.isolated_env(home, COLUMNS="1000")
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from menkyo.build_diploma import cli; cli(sys.argv[2:])",
         str(src_dir), "--help"],
        env=env, cwd=str(root), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(str(root), "<CHECKOUT>")


def _flags(help_text):
    return set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", help_text))


def test_ac7_cli_help_unchanged(tmp_path):
    """Every flag is as it was at the start of the item.

    Superseded in part by plain-white (docs/work/plain-white/acceptance.md,
    "Contract changes to earlier items"): that item removes one flag and
    rewords the variant help, so this now checks the flags only.  No flag but
    the ones plain-white and the later flag-removal item remove may
    disappear, and none may appear.
    """
    if _git("cat-file", "-e", f"{BEFORE}^{{commit}}") is None:
        pytest.skip(f"{BEFORE} not available (no git, or a shallow clone)")
    old = tmp_path / "old"
    old.mkdir()
    archive = subprocess.run(["git", "-C", str(support.REPO), "archive", BEFORE, "src/menkyo"],
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
    # A checkout of its own, so its --out default is <CHECKOUT>/build too.
    (old / "pyproject.toml").write_text('[project]\nname = "menkyo"\nversion = "0.1.0"\n')
    home = tmp_path / "help-home"
    home.mkdir()
    removed_by_plain_white = {"--pr" + "ess"}
    removed_later = {"--super" + "sample"}
    assert _flags(_help(support.SRC, home)) == \
        _flags(_help(old / "src", home)) - removed_by_plain_white \
        - removed_later


# ------------------------------------------------------------------ AC-8 ----
def test_ac8_config_save_kept():
    from menkyo import config as config_mod
    assert callable(config_mod.save)
    tests = (support.TESTS / "regression" / "test_config.py").read_text(encoding="utf-8")
    assert "def test_save_load_round_trip" in tests
    assert "def test_save_defaults_to_the_user_config" in tests


# ------------------------------------------------------------------ AC-9 ----
def test_ac9_suite_collects(home):
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                        "-p", "no:cacheprovider"],
                       cwd=str(support.REPO), env=support.isolated_env(home),
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    ids = r.stdout.splitlines()
    for gone in REMOVED_TESTS:
        assert not [i for i in ids if i.startswith(gone)], gone
    assert any(i.startswith("tests/regression/test_golden.py") for i in ids)


# ----------------------------------------------------------------- AC-10 ----
def test_ac10_readme():
    readme = (support.REPO / "README.md").read_text(encoding="utf-8")
    headings = [l for l in readme.splitlines() if l.startswith("#")]
    for h in headings:
        assert not re.search(r"\bmac\b|web page|the app\b|building the app", h, re.I), h
    assert "dojo-portal" in readme
    assert "uv run menkyo" in readme
    # the --json contract the portal relies on is still documented
    for event in ('"progress"', '"file"', '"done"', '"error"'):
        assert event in readme, event


def test_ac10_claude_md_layout():
    text = (support.REPO / "CLAUDE.md").read_text(encoding="utf-8")
    layout = text.split("## Layout", 1)[1].split("\n## ", 1)[0]
    assert "src/menkyo/" in layout
    for gone in ("gui", "web", "packaging", "deploy"):
        assert gone not in layout.lower(), gone


# ----------------------------------------------------------------- AC-11 ----
# The item that removed the flag (its acceptance.md, AC-10, user-approved) rewords the last two bullets of the 2026-09-05 "Output, and
# the ... cap" entry into the past tense.  Those bullets, and nothing else,
# are left out of the byte-for-byte history comparison.  The flag's name is
# spelled in two halves: that item's AC-11 bans it from the repository.
_REWORDED_BULLETS = re.compile(
    r"^- \*\*`--super" r"sample` .*?(?=\n\n## 2026-09-05 — Printing the three hand slots\n)",
    re.M | re.S)


def _without_reworded_bullets(text):
    stripped, n = _REWORDED_BULLETS.subn("<reworded bullets>", text, count=1)
    assert n == 1, "the reworded 2026-09-05 bullets were not found"
    return stripped


CLI_ONLY_HEADING = "2026-10-28 — The command is the product"


def test_ac11_decisions_entry_appended_history_untouched():
    """The cli-only entry was appended and nothing before it changed.

    Later items append entries of their own after it (plain-white did), so
    the entry is found by its heading rather than as the only new one.
    """
    text = (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")
    entries, open_ = text.split("\n## Open\n", 1)
    old = _git("show", f"{BEFORE}:DECISIONS.md")
    if old is not None:
        old_entries = old.stdout.split("\n## Open\n", 1)[0]
        assert _without_reworded_bullets(entries).startswith(
            _without_reworded_bullets(old_entries)), "an earlier entry was changed"
        assert CLI_ONLY_HEADING not in old_entries
    blocks = re.split(r"^(?=## )", entries, flags=re.M)
    mine = [b for b in blocks if b.startswith("## " + CLI_ONLY_HEADING)]
    assert len(mine) == 1, [b.splitlines()[0] for b in blocks if b.startswith("## ")]
    new = mine[0]
    assert "portal" in new and "--json" in new
    assert "release" in new.lower() and "uv build" in new     # AC-14's reason
    for word in ("app", "web", "deploy"):
        assert word in new.lower(), word


# ----------------------------------------------------------------- AC-12 ----
def test_ac12_recipient_docs_kept():
    for f in ("docs/three_up.png", "docs/README.md", "docs/dan-explained.md",
              "docs/renshi-explained.md", "docs/shihan-explained.md"):
        assert (support.REPO / f).is_file(), f


# ----------------------------------------------------------------- AC-14 ----
# (AC-13, the workflow, is test_ac_release.py::test_ac14_*.)
def test_ac14_readme_builds_the_wheel_locally():
    readme = (support.REPO / "README.md").read_text(encoding="utf-8")
    assert "uv build --wheel" in readme
    assert "menkyo --version" in readme
    assert re.search(r"version[^\n]*pyproject\.toml|pyproject\.toml[^\n]*version", readme)
    # the consumer installs the built file, e.g. a uv path source
    assert re.search(r"(uv add|uv pip install|pip install)[^\n]*\.whl", readme)
    assert "git tag" not in readme


def test_ac14_claude_md_has_no_release_flow():
    text = (support.REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "uv build --wheel" in text
    assert not re.search(r"tags `?v", text), "no tag-driven release any more"
    assert "publishes" not in text
