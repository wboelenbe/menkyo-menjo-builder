"""remove-supersample: the --supersample flag and every supersampling code
path are gone; output without the flag is what it was.

Contract: docs/work/remove-supersample/acceptance.md.  AC-6 is also
tests/regression/test_golden.py (the `inked-svg` case took the place of
`supersample`) and AC-12 is the rest of the suite.  Runs use the shipped
example.  Migrated for render-without-inkscape: there is no stand-in inkscape
any more, runs render for real, and AC-6 checks the text layer's pixel size
instead of the Inkscape call that asked for 600 dpi.

This file and tests/regression/golden_cases.py are the only places outside
DECISIONS.md and docs/work/ that may still spell the flag's name; AC-11
excludes them from its scan.
"""

import inspect
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd

THIS = Path(__file__).resolve()
EX = str(support.EXAMPLE)
WORD = re.compile(r"supersampl", re.I)
UNRECOGNIZED = "unrecognized arguments: --supersample"

# Every form a caller could have used; `--supers` is the unambiguous prefix
# argparse accepted until now.  `1` is the old default, so even passing the
# no-op value is now an error.
FORMS = [["--supersample", "2"], ["--supersample=2"], ["--supersample", "1"],
         ["--supersample", "4"], ["--supersample", "5"], ["--supers", "2"]]
FORM_IDS = ["space-2", "equals-2", "old-default-1", "4", "5", "prefix"]


# ----------------------------------------------------------------- helpers ----
def _cli(argv, capsys):
    """cli() in-process; (exit code, events, stderr)."""
    with pytest.raises(SystemExit) as e:
        bd.cli(argv)
    cap = capsys.readouterr()
    return e.value.code, support.events(cap.out), cap.err


def _help(home, exe=None, cwd=support.REPO):
    env = support.isolated_env(home, COLUMNS="1000")        # no wrapping
    r = support.run_menkyo(["-c", EX, "--help"], env, cwd, exe=exe)
    assert r.returncode == 0, r.stderr
    return r.stdout


_WALK_SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist",
              "crest", "ref"}


def repo_files():
    """Tracked and untracked-but-not-ignored files, relative to REPO; without
    git (the Docker image), a walk that skips what .gitignore would."""
    if shutil.which("git") and (support.REPO / ".git").exists():
        r = subprocess.run(["git", "-C", str(support.REPO), "ls-files", "-z", "--cached",
                            "--others", "--exclude-standard"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return sorted({n for n in r.stdout.split("\0")
                           if n and (support.REPO / n).is_file()})
    out = []
    for root, dirs, files in os.walk(support.REPO):
        dirs[:] = [d for d in dirs if d not in _WALK_SKIP]
        for f in files:
            if f == "dojo.toml" or f.endswith(".pyc"):
                continue
            out.append(Path(root, f).relative_to(support.REPO).as_posix())
    return sorted(out)


def _decisions():
    return (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")


def _sections(text):
    """{heading line: body} for every `## ` section.  The dash after an
    entry's date is read as an en dash, whichever it is: house-style-sweep
    changed it from an em dash."""
    parts = re.split(r"^(## .*)$", text, flags=re.M)
    return {re.sub(r"^(## \d{4}-\d{2}-\d{2}) — ", r"\1 – ", parts[i].strip()): parts[i + 1]
            for i in range(1, len(parts) - 1, 2)}


# ------------------------------------------------------------------ AC-1 ----
@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_ac1_flag_is_unrecognized(form, home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay", "-f", "svg", *form,
                            "-d", "", f"--out={out}"], support.isolated_env(home), tmp_path)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert r.stdout == ""
    assert r.stderr.startswith("usage: menkyo")
    assert f"unrecognized arguments: {form[0]}" in r.stderr
    assert "Traceback" not in r.stderr
    assert "must be between" not in r.stderr
    assert not out.exists(), "nothing may be written before the error"


def test_ac1_flag_is_unrecognized_by_list_too(home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "--list", "--supersample", "2", f"--out={out}"],
                           support.isolated_env(home), tmp_path)
    assert r.returncode == 2 and r.stdout == ""
    assert UNRECOGNIZED in r.stderr
    assert not out.exists()


# ------------------------------------------------------------------ AC-2 ----
@pytest.mark.parametrize("form", FORMS, ids=FORM_IDS)
def test_ac2_flag_is_a_json_error(form, tmp_path, capsys):
    out = tmp_path / "out"
    code, ev, err = _cli(["-c", EX, "-a", "dan", "-v", "overlay", "-f", "svg", *form,
                          "-d", "", f"--out={out}", "--json"], capsys)
    assert code == 1
    assert len(ev) == 1 and ev[0]["event"] == "error", ev
    assert f"unrecognized arguments: {form[0]}" in ev[0]["message"]
    assert "must be between" not in ev[0]["message"]
    assert err == ""
    assert not out.exists()


def test_ac2_json_error_from_a_subprocess(home, tmp_path):
    """What the portal would see: one JSON line on stdout, exit 1."""
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "--awards=dan", "--variants=overlay", "--formats=pdf",
                            "--name=", "--rank=", "--date=", "--supersample=2",
                            f"--out={out}", "--json"], support.isolated_env(home), tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert len(ev) == 1 and ev[0]["event"] == "error"
    assert UNRECOGNIZED in ev[0]["message"]
    assert not out.exists()


def test_ac2_list_json_error(home, tmp_path, capsys):
    code, ev, err = _cli(["-c", EX, "--list", "--supersample", "2", "--json"], capsys)
    assert code == 1 and [e["event"] for e in ev] == ["error"]
    assert UNRECOGNIZED in ev[0]["message"]
    assert "planned" not in [e["event"] for e in ev]


# ------------------------------------------------------------------ AC-3 ----
def test_ac3_range_message_is_gone():
    src = inspect.getsource(bd)
    assert "must be between 1 and 4" not in src
    assert "32767" not in src


# ------------------------------------------------------------------ AC-4 ----
def test_ac4_help(home):
    text = _help(home)
    assert not WORD.search(text), "the help still mentions supersampling"
    for kept in ("--awards", "--variants", "--formats", "--no-ink", "--name", "--rank",
                 "--date", "--honorific", "--suffix", "--dpi", "--all", "--out", "--clean",
                 "--list", "--json", "--version", "--example-config", "--config"):
        assert kept in text, kept


# ------------------------------------------------------------------ AC-5 ----
def test_ac5_no_supersample_parameter():
    # Was pinned to (base, verb, heading, kw, env); render-without-inkscape
    # dropped env (there is no tool environment), so only the substance is
    # kept: the text layer takes no supersampling parameter.
    params = list(inspect.signature(bd._inked_text_image).parameters)
    assert params[:4] == ["base", "verb", "heading", "kw"], params
    assert not any(WORD.search(p) for p in params), params
    for fn in (bd.build_one, bd.main, bd.cli, bd.render, bd.document):
        assert not any(WORD.search(p) for p in inspect.signature(fn).parameters), fn.__name__


def test_ac5_package_never_mentions_it():
    hits = []
    for p in sorted(support.PACKAGE.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            hits += [f"{p.relative_to(support.REPO)}:{i}" for i, line
                     in enumerate(text.splitlines(), 1) if WORD.search(line)]
    assert not hits, hits


# ------------------------------------------------------------------ AC-6 ----
@pytest.mark.render
def test_ac6_text_layer_exported_at_600_dpi(tmp_path):
    """Every inked overlay's text layer is the 600 dpi render of its box, as
    a run without the flag always was.  (Was: the Inkscape call asked for
    --export-dpi=600; render-without-inkscape has no Inkscape call.)"""
    from PIL import Image
    out = tmp_path / "out"
    bd.main(["-c", EX, "-a", "all", "-v", "overlay", "-f", "svg", "-d", "",
             f"--out={out}"])
    layers = sorted(out.glob("*-textlayer.png"))
    assert len(layers) == 3
    for png in layers:
        svg = (out / png.name.replace("-textlayer.png", ".svg")).read_text(encoding="utf-8")
        m = re.search(r'<image x="[\d.]+" y="[\d.]+" width="([\d.]+)" height="([\d.]+)"', svg)
        w_mm, h_mm = float(m.group(1)), float(m.group(2))
        with Image.open(png) as im:
            w, h = im.size
        assert abs(w - w_mm * 600 / 25.4) <= 1 and abs(h - h_mm * 600 / 25.4) <= 1, png.name
    assert bd.INK_DPI == 600.0


# ------------------------------------------------------------------ AC-7 ----
def test_ac7_golden_case_replaced():
    """The regression case that passed --supersample 2 is now the same run
    without it, pinning the SVG and text layer it pinned before."""
    import sys
    sys.path.insert(0, str(support.TESTS / "regression"))
    from golden_cases import CASES
    from golden_lib import load_manifest
    ids = [c["id"] for c in CASES]
    assert "supersample" not in ids and "inked-svg" in ids
    case = next(c for c in CASES if c["id"] == "inked-svg")
    assert case["argv"] == ["-a", "dan", "-v", "overlay", "-f", "svg", "-d", ""]
    golden = load_manifest()["cases"]["inked-svg"]
    assert golden["files"]["dan-overlay-sample.svg"] == (
        "ccfc51622a51d07f3faa1bf7106ab513eb1d5c2df34f1890016b98877c860afc")
    assert golden["textlayers"]["dan-overlay-sample-textlayer.svg"] == (
        "97caf31f9d3178728aa186ed41bfef46980b97a43a8ff6d34d4248f938397edc")
    assert not any(WORD.search(a) for c in CASES for a in c["argv"])


# ------------------------------------------------------------------ AC-8 ----
@pytest.mark.render
def test_ac8_real_render_text_layer_is_600_dpi(session_home, tmp_path):
    """A real render: the shipped text layer is the 600 dpi render of the
    <image> box, graded, RGBA, and nothing resampled it."""
    from PIL import Image
    import numpy as np
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay", "-f", "svg,pdf",
                            "-d", "", f"--out={out}", "--json"],
                           support.isolated_env(session_home), tmp_path, timeout=1800)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    ev = support.events(r.stdout)
    assert ev[-1]["event"] == "done"
    assert [e["stage"] for e in ev if e["event"] == "progress"] == ["text", "ink", "pdf"]
    svg = (out / "dan-overlay-a3-sample.svg").read_text(encoding="utf-8")
    m = re.search(r'<image x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                  r'xlink:href="dan-overlay-a3-sample-textlayer\.png"', svg)
    assert m, "no <image> for the text layer"
    w_mm, h_mm = float(m.group(3)), float(m.group(4))
    with Image.open(out / "dan-overlay-a3-sample-textlayer.png") as im:
        assert im.mode == "RGBA"
        w, h = im.size
        a = np.asarray(im)
    assert abs(w - w_mm * 600 / 25.4) <= 2 and abs(h - h_mm * 600 / 25.4) <= 2, \
        ((w, h), (w_mm, h_mm))
    inked = a[..., 3] > 0
    assert inked.any()
    assert (a[inked][:, :3] == (17, 17, 17)).all(), "not ink_layer's output"


# ------------------------------------------------------------------ AC-9 ----
@pytest.mark.slow
@pytest.mark.render
def test_ac9_installed_wheel(installed, home, tmp_path):
    """From outside the checkout: the same contract as from the checkout."""
    exe = [str(installed["menkyo"])]
    env = support.isolated_env(home)
    site = next(installed["venv"].glob("lib/python*/site-packages"))
    for p in (site / "menkyo").rglob("*.py"):
        assert not WORD.search(p.read_text(encoding="utf-8")), p

    out = tmp_path / "out"
    r = support.run_menkyo(["-c", EX, "-a", "dan", "--supersample", "2", f"--out={out}"],
                           env, tmp_path, exe=exe)
    assert r.returncode == 2 and r.stdout == "" and UNRECOGNIZED in r.stderr

    r = support.run_menkyo(["-c", EX, "-a", "dan", "--supersample=2", f"--out={out}",
                            "--json"], env, tmp_path, exe=exe)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert len(ev) == 1 and ev[0]["event"] == "error" and UNRECOGNIZED in ev[0]["message"]

    assert not WORD.search(_help(home, exe=exe, cwd=tmp_path))
    assert not out.exists()

    # and a run without it still works
    r = support.run_menkyo(["-c", EX, "-a", "dan", "-v", "overlay", "-f", "svg", "-d", "",
                            f"--out={out}", "--json"], env, tmp_path, exe=exe)
    assert r.returncode == 0, r.stdout + r.stderr
    assert support.events(r.stdout)[-1]["event"] == "done"


# ----------------------------------------------------------------- AC-10 ----
def test_ac10_readme():
    text = (support.REPO / "README.md").read_text(encoding="utf-8")
    assert not WORD.search(text)


INK_PASS = "## 2026-10-29 – The ink pass grades the alpha alone"


def test_ac10_decisions_records_the_removal():
    """A 2026-10-29 entry of its own, its heading naming the removal: not the
    ink-pass entry reworded (round 2)."""
    sections = _sections(_decisions())
    assert INK_PASS in sections, "the ink-pass entry's heading changed"
    entries = [(h, b) for h, b in sections.items()
               if h.startswith("## 2026-10-29") and h != INK_PASS
               and WORD.search(h) and "--supersample" in b
               and re.search(r"\b(removed|gone|dropped|no longer)\b", b, re.I)]
    assert entries, "no 2026-10-29 entry recording that --supersample is gone"
    # nothing left to port to the pip-only renderer
    assert any(re.search(r"inkscape", b, re.I) for _, b in entries), entries
    open_ = sections.get("## Open", "")
    assert not WORD.search(open_)


def test_ac10_decisions_no_longer_presents_it_as_current():
    text = _decisions()
    assert "The knob is exposed because it is honest to" not in text
    assert "`--supersample` is capped at 4 and defaults to 1." not in text
    assert "**`--supersample` scales the alpha alone.**" not in text
    assert "is what makes any supersampling affordable" not in text


# ----------------------------------------------------------------- AC-11 ----
ALLOWED = {
    "DECISIONS.md",                         # history, plus the removal entry
    "tests/regression/golden_cases.py",     # says which case inked-svg replaced
    THIS.relative_to(support.REPO).as_posix(),
}


def test_ac11_repository_never_mentions_it():
    hits = []
    for rel in repo_files():
        if rel in ALLOWED or rel.startswith("docs/work/"):
            continue
        try:
            text = (support.REPO / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{rel}:{i}" for i, line in enumerate(text.splitlines(), 1)
                 if WORD.search(line)]
    assert not hits, hits
