"""render-without-inkscape: the pip-only renderer replaces Inkscape.

Contract: docs/work/render-without-inkscape/acceptance.md (AC-1 .. AC-38).
The yardstick for "looks like today" is reference/ beside this file's kit,
render_without_inkscape/: Inkscape's output at 8509b85, reduced by
refkit.py, which these tests use too, so both sides are rasterised and
scored by the same code.

Every run pins -c with the shipped example or a configuration the test
writes, and HOME / XDG_CONFIG_HOME are throwaway directories.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile
from functools import lru_cache
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd

KIT = Path(__file__).resolve().parent / "render_without_inkscape"
sys.path.insert(0, str(KIT))
import refkit  # noqa: E402

REF = KIT / "reference"
META = json.loads((REF / "meta.json").read_text(encoding="utf-8"))
EX = str(support.EXAMPLE)
FONTS = support.PACKAGE / "fonts"
CREST_FONT = FONTS / "NotoSerifJP-SemiBold.otf"
CREST_SHA256 = "116d06c2b11ceba33ccb3f8c9eb1c86aba3d5761a1199fd37f74e83365e7a53d"
BASELINE = "8509b85"
DEPS = {"pillow", "numpy", "scipy", "fonttools", "pypdfium2"}

PDF_CASES = ["C-1", "C-3", "C-4", "C-4b", "C-5"]
PNG_CASES = ["C-1", "C-3", "C-4", "C-4b", "C-5", "C-8"]
OVERLAYS = ["C-1", "C-3", "C-4", "C-4b"]          # overlay and overlay-flat
WHEEL_MAX = 11_500_000                            # AC-28
OPTIONS = {"--all", "--awards", "--clean", "--config", "--date", "--dpi",
           "--example-config", "--formats", "--help", "--honorific", "--json",
           "--list", "--name", "--no-ink", "--out", "--rank", "--suffix",
           "--variants", "--version"}
SHORT = {"-a", "-c", "-d", "-f", "-h", "-n", "-o", "-r", "-v"}
EXPECTED_VERSION = "0.3.0"                        # AC-37, Q-1: the user decides


# ----------------------------------------------------------------- helpers ---
def _run(args, home, cwd, exe=None, path=None, timeout=900, **extra):
    env = support.isolated_env(home, path=path, **extra)
    return support.run_menkyo(args, env, cwd, exe=exe, timeout=timeout)


def _outputs(out):
    """{ext: path} of what a single-variant run wrote, the side raster aside."""
    found = {}
    for p in sorted(Path(out).iterdir()):
        if p.is_file() and not p.name.endswith("-textlayer.png"):
            found.setdefault(p.suffix[1:], p)
    return found


def _render(case, home, root, extra=()):
    root.mkdir(parents=True, exist_ok=True)
    out = root / case
    t0 = time.perf_counter()
    r = _run(["-c", EX, *refkit.CASES[case], *extra, f"--out={out}", "--json"],
             home, root)
    wall = time.perf_counter() - t0
    assert r.returncode == 0, f"{case}: {r.stdout[-1500:]}{r.stderr[-1500:]}"
    ev = support.events(r.stdout)
    assert ev[-1]["event"] == "done", ev[-3:]
    return dict(out=out, events=ev, wall=wall, **_outputs(out))


@pytest.fixture(scope="module")
def renders(session_home, tmp_path_factory):
    """Every case rendered once with the current code."""
    root = tmp_path_factory.mktemp("rwi-renders")
    return {case: _render(case, session_home, root) for case in refkit.CASES}


@pytest.fixture(scope="module")
def svg_renders(session_home, tmp_path_factory):
    """The inked cases with -f svg,pdf: the shipped text layer and its <image>."""
    root = tmp_path_factory.mktemp("rwi-svg")
    got = {}
    for case in ("C-1", "C-3"):
        args = [a for a in refkit.CASES[case]]
        args[args.index("-f") + 1] = "svg,pdf"
        out = root / case
        r = _run(["-c", EX, *args, f"--out={out}", "--json"], session_home, root)
        assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
        got[case] = out
    return got


@lru_cache(maxsize=1)
def _page600(pdf):
    return refkit.pdf_grey(pdf, 600)


def _ref_img(name):
    import numpy as np
    from PIL import Image
    with Image.open(REF / name) as im:
        return np.asarray(im.convert("L"))


def _cli(argv, capsys):
    """cli() in-process: (exit code, events, stderr)."""
    with pytest.raises(SystemExit) as e:
        bd.cli(argv)
    cap = capsys.readouterr()
    return e.value.code, support.events(cap.out), cap.err


def _example_text():
    return support.EXAMPLE.read_text(encoding="utf-8")


def _config(tmp_path, old, new, name="cfg.toml", text=None):
    text = text if text is not None else _example_text()
    assert old in text, old
    p = tmp_path / name
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return p


def _tree(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _assert_glyph_message(msg, ch, where):
    code = f"U+{ord(ch):04X}"
    assert ch in msg, (ch, msg)
    assert code in msg, (code, msg)
    assert re.search(r"replac", msg, re.I), f"no request for a replacement: {msg!r}"
    assert re.search(where, msg, re.I), f"does not say where it came from ({where}): {msg!r}"


def _py_files():
    return sorted(p for p in support.PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)


def _readme():
    return (support.REPO / "README.md").read_text(encoding="utf-8")


def _section(text, heading):
    part = text.split(f"\n## {heading}\n", 1)
    assert len(part) == 2, heading
    return part[1].split("\n## ", 1)[0]


def _git(*args):
    if not shutil.which("git") or not (support.REPO / ".git").exists():
        return None
    r = subprocess.run(["git", "-C", str(support.REPO), *args], capture_output=True, text=True)
    return r if r.returncode == 0 else None


def _pyproject():
    with open(support.REPO / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)


def _dep_names(deps):
    return {re.split(r"[<>=!~\[ ;]", d, maxsplit=1)[0].lower() for d in deps}


# -------------------------------------------------------------------- AC-1 ---
@pytest.mark.render
def test_ac1_renders_with_an_empty_path(home, tmp_path):
    empty = tmp_path / "emptybin"
    empty.mkdir()
    for case in ("C-1", "C-4"):
        args = list(refkit.CASES[case])
        args[args.index("-f") + 1] = "pdf"
        out = tmp_path / case
        r = _run(["-c", EX, *args, f"--out={out}", "--json"], home, tmp_path, path=str(empty))
        assert r.returncode == 0, (case, r.stdout[-1500:], r.stderr[-1500:])
        assert support.events(r.stdout)[-1]["event"] == "done"
        assert list(out.glob("*.pdf")), case


def test_ac1_no_inkscape_fontconfig_or_subprocess_in_the_package():
    hits = []
    for p in _py_files():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"inkscape|fontconfig", line, re.I) or \
                    re.search(r"^\s*(import\s+subprocess|from\s+subprocess\s+import)\b", line):
                hits.append(f"{p.relative_to(support.REPO)}:{n}: {line.strip()[:100]}")
    assert hits == [], "\n".join(hits)


@pytest.mark.render
def test_ac1_no_system_font_lookup(home, tmp_path):
    """A decoy 'Yuji Boku' wherever a font lookup by name might look, and a
    nonsense fontconfig: the PDF is byte for byte the plain run's."""
    assert CREST_FONT.is_file(), "the crest font is not vendored (AC-3)"
    args = list(refkit.CASES["C-4"])
    args[args.index("-f") + 1] = "pdf"
    plain = tmp_path / "plain"
    r = _run(["-c", EX, *args, f"--out={plain}"], home, tmp_path)
    assert r.returncode == 0, r.stderr[-1500:]

    decoy_home = tmp_path / "decoy-home"
    xdg = tmp_path / "xdg-data"
    for d in (decoy_home / ".fonts", decoy_home / "Library" / "Fonts", xdg / "fonts"):
        d.mkdir(parents=True)
        shutil.copy(CREST_FONT, d / "YujiBoku-Regular.ttf")
    decoy = tmp_path / "decoy"
    r = _run(["-c", EX, *args, f"--out={decoy}"], decoy_home, tmp_path,
             FONTCONFIG_FILE=str(tmp_path / "nonsense" / "fonts.conf"),
             FONTCONFIG_PATH=str(tmp_path / "nonsense"), XDG_DATA_HOME=str(xdg))
    assert r.returncode == 0, r.stderr[-1500:]
    a, b = _outputs(plain)["pdf"], _outputs(decoy)["pdf"]
    assert a.read_bytes() == b.read_bytes()


# -------------------------------------------------------------------- AC-2 ---
def test_ac2_dependencies():
    deps = _pyproject()["project"]["dependencies"]
    assert _dep_names(deps) == DEPS, deps
    pdfium = [d for d in deps if d.lower().startswith("pypdfium2")]
    assert re.search(r"==\s*\d", pdfium[0]), f"pypdfium2 is not pinned with ==: {pdfium}"
    fonttools = [d for d in deps if d.lower().startswith("fonttools")]
    assert re.search(r">=?\s*\d", fonttools[0]), f"fonttools has no lower bound: {fonttools}"


def test_ac2_pyproject_names_no_system_programs():
    text = (support.REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert not re.search(r"inkscape", text, re.I)
    for line in text.splitlines():
        if "system program" in line.lower():
            assert re.search(r"\b(no|none)\b", line, re.I), line


# -------------------------------------------------------------------- AC-3 ---
def test_ac3_yuji_boku_unchanged():
    path = FONTS / "YujiBoku-Regular.ttf"
    assert path.is_file()
    if _git("rev-parse", BASELINE) is None:
        pytest.skip("no git history here (the Docker image)")
    r = subprocess.run(["git", "-C", str(support.REPO), "show",
                        f"{BASELINE}:src/menkyo/fonts/YujiBoku-Regular.ttf"],
                       capture_output=True, check=True)
    assert r.stdout == path.read_bytes()


def test_ac3_crest_font_is_noto_serif_jp_semibold():
    assert CREST_FONT.is_file()
    assert support.sha256(CREST_FONT.read_bytes()) == CREST_SHA256


def _crest_licence():
    cands = [p for p in FONTS.iterdir() if p.is_file() and p.name != "OFL.txt"
             and p.suffix.lower() in (".txt", "") and p.name != "METADATA.pb"]
    good = [p for p in cands
            if "sil open font license" in p.read_text(encoding="utf-8", errors="replace").lower()]
    assert good, f"no OFL licence for the crest font in {FONTS}: {[p.name for p in cands]}"
    return good[0]


def test_ac3_crest_font_licence():
    lic = _crest_licence()
    files = _pyproject()["project"]["license-files"]
    assert f"src/menkyo/fonts/{lic.name}" in files, files


def test_ac3_notice():
    notice = (support.REPO / "NOTICE").read_text(encoding="utf-8")
    assert "Noto Serif JP" in notice
    section = notice.split("Noto Serif JP", 1)[1]
    assert re.search(r"Open Font License|OFL", section)
    assert re.search(r"noto-cjk|Serif2\.003", notice)
    licence = _section(_readme(), "Licence")
    assert re.search(r"\bfonts\b", licence), licence


# -------------------------------------------------------------------- AC-4 ---
def test_ac4_inkscape_helpers_removed():
    from menkyo import paths
    for gone in ("find_tool", "require_tool", "tool_env", "system_font_dirs",
                 "_EXTRA_BIN", "_INSTALL_HINT"):
        assert not hasattr(paths, gone), gone
    assert not hasattr(bd, "_font_env")
    for kept in ("checkout_root", "resource", "user_data_dir", "default_output_dir"):
        assert callable(getattr(paths, kept)), kept


@pytest.mark.render
def test_ac4_no_fontconfig_dir_left(renders):
    for case, r in renders.items():
        names = sorted(p.name for p in r["out"].iterdir())
        assert ".fontconfig" not in names and ".work" not in names, (case, names)


# ------------------------------------------------------------- AC-5, AC-6 ---
FLAG_CASES = [
    (["--name", "𠮷田"], "𠮷", r"--name"),
    (["--name", "ㇰロ"], "ㇰ", r"--name"),
    (["--rank", "𠮷段"], "𠮷", r"--rank"),
    (["--honorific", "😀"], "😀", r"--honorific"),
]
BASE = ["-a", "dan", "-v", "overlay,overlay-flat", "-f", "pdf,png,svg"]


def _defaults(flags):
    """Every fill-in given explicitly; the one under test wins."""
    given = dict(zip(flags[::2], flags[1::2]))
    out = []
    for flag, value in (("--name", "ヤン・ヤンセン"), ("--rank", "2"),
                        ("--date", "2024-07-01"), ("--honorific", "殿")):
        out.append(f"{flag}={given.get(flag, value)}")
    return out


@pytest.mark.parametrize("flags, ch, where", FLAG_CASES, ids=[c[0][1] for c in FLAG_CASES])
def test_ac5_missing_glyph_in_a_flag(flags, ch, where, home, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("already here")
    before = _tree(out)
    r = _run(["-c", EX, *BASE, *_defaults(flags), f"--out={out}"], home, tmp_path)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr[-800:])
    assert r.stdout == ""
    assert "Traceback" not in r.stderr
    _assert_glyph_message(r.stderr, ch, where)
    assert _tree(out) == before, "the output directory changed"
    assert not (out / ".work").exists()


@pytest.mark.parametrize("flags, ch, where", FLAG_CASES, ids=[c[0][1] for c in FLAG_CASES])
def test_ac6_missing_glyph_json(flags, ch, where, home, tmp_path):
    out = tmp_path / "out"
    r = _run(["-c", EX, *BASE, *_defaults(flags), f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"], ev
    _assert_glyph_message(ev[0]["message"], ch, where)
    assert _tree(out) == {}


# -------------------------------------------------------------------- AC-7 ---
CONFIG_CASES = [
    ('name = "〇〇流柔術"', 'name = "𠮷流柔術"', "𠮷", r"\bart\b"),
    ('name = "〇〇道場"', 'name = "𠮷道場"', "𠮷", r"\bdojo\b"),
    ('title = "師範"', 'title = "𠮷範"', "𠮷", r"\btitle\b"),
    ('name = "山田太郎"', 'name = "𠮷田太郎"', "𠮷", r"\bsigner\b"),
    ('text = "柔能制剛"', 'text = "柔能𠮷剛"', "𠮷", r"\bmotto\b"),
    ('text = "柔能制剛"', 'text = "柔能😀剛"', "😀", r"\bmotto\b"),
    ('heading = "段位免状"', 'heading = "段位𠮷状"', "𠮷", r"\bheading\b"),
    ('formula = "右授与ス"', 'formula = "右𠮷与ス"', "𠮷", r"\bformula\b"),
    ('crest_ring = "〇〇道場"', 'crest_ring = "한〇道場"', "한", r"crest_ring"),
]


@pytest.mark.parametrize("old, new, ch, where", CONFIG_CASES,
                         ids=[c[1].split(" =")[0] + ":" + c[2] for c in CONFIG_CASES])
def test_ac7_missing_glyph_in_config(old, new, ch, where, home, tmp_path):
    cfg = _config(tmp_path, old, new)
    out = tmp_path / "out"
    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf",
              "--name=", "--rank=", "--date=", f"--out={out}"], home, tmp_path)
    assert r.returncode == 1, (r.returncode, r.stderr[-800:])
    assert r.stdout == "" and "Traceback" not in r.stderr
    _assert_glyph_message(r.stderr, ch, where)
    assert _tree(out) == {}

    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf",
              "--name=", "--rank=", "--date=", f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"], ev
    _assert_glyph_message(ev[0]["message"], ch, where)


# AC-5..8 scope (Agreement 5): exactly what will be drawn is checked, and a
# fill-in that comes from the configuration is named by its key.
def _sample(tmp_path, key, value):
    old = {"name": 'name = "ジョン・ドウ"', "rank": 'rank = "5"'}[key]
    return _config(tmp_path, old, f'{key} = "{value}"', name=f"sample-{key}.toml")


def test_ac5_sample_name_is_named_by_its_key(home, tmp_path):
    cfg = _sample(tmp_path, "name", "𠮷田")
    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf", "--rank=",
              "--date=", f"--out={tmp_path / 'out'}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"], ev
    _assert_glyph_message(ev[0]["message"], "𠮷", r"\[sample\] name")


@pytest.mark.render
def test_ac5_sample_rank_only_where_a_grade_is_drawn(home, tmp_path):
    cfg = _sample(tmp_path, "rank", "𠮷段")
    common = ["--name=", "--date=", "-v", "overlay-flat", "-f", "pdf", "--json"]
    # a licence has no grade column: the sample rank is not drawn, not checked
    r = _run(["-c", cfg, "-a", "shihan", *common, f"--out={tmp_path / 'a'}"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    r = _run(["-c", cfg, "-a", "dan", *common, f"--out={tmp_path / 'b'}"], home, tmp_path)
    assert r.returncode == 1
    _assert_glyph_message(support.events(r.stdout)[-1]["message"], "𠮷", r"\[sample\] rank")
    # an explicit --rank is drawn on a licence too, so it is checked there
    r = _run(["-c", EX, "-a", "shihan", "--rank=𠮷段", *common, f"--out={tmp_path / 'c'}"],
             home, tmp_path)
    assert r.returncode == 1
    _assert_glyph_message(support.events(r.stdout)[-1]["message"], "𠮷", r"--rank")


@pytest.mark.render
def test_ac5_honorific_only_with_a_name(home, tmp_path):
    cfg = _config(tmp_path, 'honorific = "殿"', 'honorific = "😀"')
    common = ["-a", "dan", "-v", "overlay-flat", "-f", "pdf", "--rank=", "--date=", "--json"]
    r = _run(["-c", cfg, *common, "--name=", f"--out={tmp_path / 'a'}"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    r = _run(["-c", cfg, *common, "--name=ヤン", f"--out={tmp_path / 'b'}"], home, tmp_path)
    assert r.returncode == 1
    _assert_glyph_message(support.events(r.stdout)[-1]["message"], "😀", r"honorific")


@pytest.mark.render
def test_ac5_only_the_selected_awards_are_checked(home, tmp_path):
    cfg = _config(tmp_path, 'heading = "錬士免許状"', 'heading = "錬士𠮷許状"')
    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf", "--name=", "--rank=",
              "--date=", f"--out={tmp_path / 'out'}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]


# -------------------------------------------------------------------- AC-8 ---
def test_ac8_nothing_written_for_any_award(home, tmp_path):
    cfg = _config(tmp_path, 'heading = "錬士免許状"', 'heading = "錬士𠮷許状"')
    out = tmp_path / "out"
    r = _run(["-c", cfg, "-a", "all", "-v", "overlay,overlay-flat", "-f", "pdf",
              "--name=", "--rank=", "--date=", f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"], ev
    assert _tree(out) == {}


def test_ac8_clean_keeps_the_directory_on_error(home, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "earlier.pdf").write_bytes(b"%PDF-1.4 an earlier certificate")
    before = _tree(out)
    r = _run(["-c", EX, "-a", "dan", "-v", "overlay-flat", "--name=𠮷田", "--rank=",
              "--date=", "--clean", f"--out={out}"], home, tmp_path)
    assert r.returncode == 1
    assert _tree(out) == before


# -------------------------------------------------------------------- AC-9 ---
def test_ac9_list_is_not_checked(home, tmp_path):
    plain = _run(["-c", EX, "--list", "-a", "dan", "-n", "ヤン", f"--out={tmp_path / 'o'}"],
                 home, tmp_path)
    bad = _run(["-c", EX, "--list", "-a", "dan", "-n", "𠮷田", f"--out={tmp_path / 'o'}"],
               home, tmp_path)
    assert plain.returncode == bad.returncode == 0
    assert bad.stdout == "dan-overlay-𠮷田.pdf\n"
    assert not (tmp_path / "o").exists()


@pytest.mark.render
def test_ac9_space_slash_colon_render(home, tmp_path):
    out = tmp_path / "out"
    r = _run(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-f", "pdf",
              "--name=ヤン　ヤンセン/x:y", "--rank=", "--date=", f"--out={out}", "--json"],
             home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    assert support.events(r.stdout)[-1]["event"] == "done"


TRACED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
          '<path d="M 100 100 l 800 0 l 0 800 c -100 50 -700 50 -800 0 z '
          'M 300 300 L 700 300 L 700 700 L 300 700 Z"/></svg>')


@pytest.mark.render
def test_ac9_traced_glyph_stands_in_for_the_font(home, tmp_path):
    text = _example_text().replace("traced_glyphs = false", "traced_glyphs = true")
    cfg = _config(tmp_path, 'crest_ring = "〇〇道場"', 'crest_ring = "한〇道場"', text=text)
    (tmp_path / "crest").mkdir()
    (tmp_path / "crest" / "한.svg").write_text(TRACED, encoding="utf-8")
    out = tmp_path / "out"
    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf",
              "--name=", "--rank=", "--date=", f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    pdf = _outputs(out)["pdf"]
    # the traced square is drawn where the ring's first character sits
    page = refkit.pdf_grey(pdf, 300)
    ring = META["cases"]["C-5"]["ring"][0]
    box = (ring[1] - 2.0, ring[2] - 2.0, ring[1] + 2.0, ring[2] + 2.0)
    assert refkit.ink_sum(refkit.crop(page, box, 300)) > 0, "no traced glyph drawn"

    # a ring character with no traced file still needs the font
    (tmp_path / "crest" / "한.svg").unlink()
    r = _run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf",
              "--name=", "--rank=", "--date=", f"--out={tmp_path / 'out2'}"], home, tmp_path)
    assert r.returncode == 1
    _assert_glyph_message(r.stderr, "한", r"crest_ring")


def test_ac9_traced_glyph_with_an_arc_is_refused(home, tmp_path):
    """Agreement 6: the writer takes M L H V C S Q T Z, absolute and relative,
    and refuses A; the error names the crest file."""
    text = _example_text().replace("traced_glyphs = false", "traced_glyphs = true")
    cfg = _config(tmp_path, 'crest_ring = "〇〇道場"', 'crest_ring = "한〇道場"', text=text)
    (tmp_path / "crest").mkdir()
    traced = tmp_path / "crest" / "한.svg"
    traced.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                      '<path d="M 100 500 A 400 400 0 0 1 900 500 Z"/></svg>', encoding="utf-8")
    out = tmp_path / "out"
    args = ["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "pdf", "--name=", "--rank=",
            "--date=", f"--out={out}"]
    r = _run(args, home, tmp_path)
    assert r.returncode == 1 and "Traceback" not in r.stderr, r.stderr[-800:]
    assert str(traced) in r.stderr or "한.svg" in r.stderr, r.stderr[-800:]
    r = _run(args + ["--json"], home, tmp_path)
    ev = support.events(r.stdout)
    kinds = [e["event"] for e in ev]
    assert r.returncode == 1 and kinds[-1] == "error" and kinds.count("error") == 1, ev
    assert "done" not in kinds and "한.svg" in ev[-1]["message"] + ev[-1].get("detail", "")
    assert not list(out.glob("*.pdf")) and not (out / ".work").exists()


# ------------------------------------------------------------------- AC-10 ---
def _copy_run(site, home, tmp_path, *extra):
    out = tmp_path / "out"
    args = ["-c", EX, *refkit.CASES["C-4"], f"--out={out}", *extra]
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from menkyo.build_diploma import cli; cli(sys.argv[2:])", str(site), *args],
        env=support.isolated_env(home), cwd=str(tmp_path), capture_output=True, text=True,
        timeout=600)
    return r, out


def test_ac10_missing_body_font(home, tmp_path):
    site = tmp_path / "site"
    pkg = support.copy_package(site)
    font = pkg / "fonts" / "YujiBoku-Regular.ttf"
    font.unlink()
    r, out = _copy_run(site, home, tmp_path)
    assert r.returncode == 1, r.stderr[-800:]
    assert str(font) in r.stderr, r.stderr[-800:]
    assert "Traceback" not in r.stderr
    assert _tree(out) == {}


def test_ac10_truncated_crest_font(home, tmp_path):
    site = tmp_path / "site"
    pkg = support.copy_package(site)
    font = pkg / "fonts" / "NotoSerifJP-SemiBold.otf"
    assert font.is_file(), "the crest font is not vendored (AC-3)"
    data = font.read_bytes()
    font.write_bytes(data[:len(data) // 2])
    r, out = _copy_run(site, home, tmp_path)
    assert r.returncode == 1, r.stderr[-800:]
    assert str(font) in r.stderr, r.stderr[-800:]
    assert "Traceback" not in r.stderr
    assert _tree(out) == {}


def test_ac10_font_error_json(home, tmp_path):
    site = tmp_path / "site"
    pkg = support.copy_package(site)
    font = pkg / "fonts" / "YujiBoku-Regular.ttf"
    font.unlink()
    r, out = _copy_run(site, home, tmp_path, "--json")
    assert r.returncode == 1
    ev = support.events(r.stdout)
    kinds = [e["event"] for e in ev]
    assert kinds[-1] == "error" and kinds.count("error") == 1 and "done" not in kinds, ev
    assert str(font) in ev[-1]["message"] + ev[-1].get("detail", "")


# ------------------------------------------------------------------- AC-11 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac11_page_and_validity(case, renders):
    pdf = renders[case]["pdf"]
    s = refkit.pdf_summary(pdf)
    assert s["pages"] == 1
    assert s["mediabox"] is not None and len(s["mediabox"]) == 4
    x0, y0, x1, y1 = s["mediabox"]
    assert abs(x1 - x0 - 1190.55) <= 0.01 and abs(y1 - y0 - 841.89) <= 0.01, s["mediabox"]
    assert s["rotate"] % 360 == 0
    assert refkit.xref_problems(pdf) == []
    n, (w, h) = refkit.pdf_info(pdf)
    assert n == 1 and abs(w - 1190.55) <= 0.01 and abs(h - 841.89) <= 0.01


# ------------------------------------------------------------------- AC-12 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac12_outlines_no_fonts(case, renders):
    s = refkit.pdf_summary(renders[case]["pdf"])
    assert s["font_objects"] == 0, s
    assert s["text_ops"] == 0, s
    if case not in refkit.INKED:            # glyphs inline, no Form reuse
        assert s["path_ops"] > 1000, s["path_ops"]
    else:
        assert s["path_ops"] > 50, s["path_ops"]


# ------------------------------------------------------------------- AC-13 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac13_images(case, renders):
    s = refkit.pdf_summary(renders[case]["pdf"])
    if case in refkit.INKED:
        assert len(s["images"]) == 1, s["images"]
        im = s["images"][0]
        assert im["cs"] == "/DeviceGray" and im["smask"] and im["smask_cs"] == "/DeviceGray", im
    else:
        assert s["images"] == [] and s["smasks"] == [], s


# ------------------------------------------------------------------- AC-14 ---
# g/G, or a colour space set to DeviceGray (cs/CS) and colours in it (sc...)
GREY_OPS = {"g", "G", "cs /DeviceGray", "CS /DeviceGray", "sc", "SC", "scn", "SCN"}


@pytest.mark.render
@pytest.mark.parametrize("case", [c for c in OVERLAYS if c in PDF_CASES])
def test_ac14_overlays_are_grey(case, renders):
    s = refkit.pdf_summary(renders[case]["pdf"])
    bad = {k: v for k, v in s["colour_ops"].items() if k not in GREY_OPS}
    assert bad == {}, s["colour_ops"]
    assert all(g in (None, "/DeviceGray") for g in s["groups"]), s["groups"]
    for im in s["images"]:
        assert im["cs"] == "/DeviceGray" and im["smask_cs"] in (None, "/DeviceGray"), im


@pytest.mark.render
@pytest.mark.parametrize("case", [c for c in OVERLAYS if c in PDF_CASES])
def test_ac14_overlay_raster_has_no_colour(case, renders):
    import numpy as np
    rgb = refkit.pdf_rgb(renders[case]["pdf"], 100).astype(int)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    assert int(chroma.max()) == 0, int(chroma.max())


@pytest.mark.render
def test_ac14_proof_keeps_its_guide_colours(renders):
    import numpy as np
    from PIL import Image
    s = refkit.pdf_summary(renders["C-5"]["pdf"])
    assert s["colour_ops"].get("RG", 0) + sum(
        v for k, v in s["colour_ops"].items() if k.startswith("SC")) > 0, s["colour_ops"]
    with Image.open(renders["C-5"]["png"]) as im:
        rgba = np.asarray(im.convert("RGBA")).astype(int)
    # the stock-border rectangle's left edge, x = 22 mm, dashed: some of it
    k = 300 / 25.4
    strip = rgba[round(40 * k):round(250 * k), round(21.6 * k):round(22.4 * k)]
    solid = strip[strip[..., 3] == 255][:, :3]
    target = np.array([216, 201, 168])
    assert len(solid) and (np.abs(solid - target).max(axis=1) <= 24).sum() > 50, \
        "the stock-border guide is not #d8c9a8"


# ------------------------------------------------------------------- AC-15 ---
@pytest.mark.render
@pytest.mark.parametrize("case", ["C-1", "C-4"])
def test_ac15_deterministic(case, session_home, tmp_path):
    a = _render(case, session_home, tmp_path / "a")
    b = _render(case, session_home, tmp_path / "b")
    for ext in ("pdf", "png"):
        assert a[ext].read_bytes() == b[ext].read_bytes(), ext


# ------------------------------------------------------------------- AC-17 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PNG_CASES)
def test_ac17_png(case, renders):
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    ref = META["cases"][case]["png"]
    want_dpi = 150 if case == "C-8" else 300
    with Image.open(renders[case]["png"]) as im:
        assert list(im.size) == ref["size"], (im.size, ref["size"])
        dpi = im.info.get("dpi")
        # pHYs is whole pixels per metre: 150 dpi is 5905.5, so either rounding
        assert dpi and all(abs(float(d) - want_dpi) <= 0.05 for d in dpi), dpi
        allowed = ("RGBA",) if refkit.variant_of(case) == "proof" else ("RGBA", "LA")
        assert im.mode in allowed, im.mode
        rgba = np.asarray(im.convert("RGBA")).astype(int)
    assert rgba[5, 5, 3] == 0, "not transparent where nothing is drawn"
    solid = ndimage.binary_erosion(rgba[..., 3] == 255, iterations=2)
    assert solid.sum() > 1000
    if refkit.variant_of(case) != "proof":
        med = np.median(rgba[..., :3][solid], axis=0)
        assert np.abs(med - 17).max() <= 2, med
        seen = rgba[..., 3] > 32
        chroma = rgba[..., :3].max(axis=2) - rgba[..., :3].min(axis=2)
        assert int(chroma[seen].max()) <= 12


# ------------------------------------------------------------------- AC-18 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac18_page_pdf(case, renders):
    a = _ref_img(f"{case}-pdf150.png").astype(float)
    b = refkit.pdf_grey(renders[case]["pdf"], 150).astype(float)
    assert a.shape == b.shape, (a.shape, b.shape)
    b2, (dy, dx) = refkit.align(a, b)
    s, m = refkit.ssim(a, b2), refkit.mad(a, b2)
    print(f"\n{case} pdf150: SSIM {s:.5f}, MAD {m:.3f}, offset ({dy:.2f}, {dx:.2f}) px")
    assert max(abs(dy), abs(dx)) <= 0.5
    assert s >= (0.97 if case in refkit.INKED else 0.98), s
    assert m <= 2.0, m


@pytest.mark.render
@pytest.mark.parametrize("case", PNG_CASES)
def test_ac18_page_png(case, renders):
    import numpy as np
    fx = META["cases"][case]["png_fixture"]
    a = _ref_img(fx["file"]).astype(float)
    im = refkit.png_on_white(renders[case]["png"])
    if fx["halved"]:
        im = refkit.half(im)
    b = np.asarray(im).astype(float)
    a, b = refkit.same_shape(a, b)
    b2, (dy, dx) = refkit.align(a, b)
    s, m = refkit.ssim(a, b2), refkit.mad(a, b2)
    print(f"\n{case} png: SSIM {s:.5f}, MAD {m:.3f}, offset ({dy:.2f}, {dx:.2f}) px")
    assert s >= 0.97, s
    assert m <= 2.0, m


# ------------------------------------------------------------------- AC-19 ---
@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac19_columns_and_crest(case, renders):
    page = _page600(str(renders[case]["pdf"]))
    bad = []
    for key, c in META["cases"][case]["crops"].items():
        x0, y0, x1, y1 = c["box_px600"]
        a = _ref_img(c["file"]).astype(float)
        b = page[y0:y1, x0:x1].astype(float)
        a, b = refkit.same_shape(a, b)
        b2, off = refkit.align(a, b)
        s = refkit.ssim(a, b2)
        region = refkit.big_region_mm2(a, b2, 600)
        ink_a, ink_b = refkit.ink_sum(a), refkit.ink_sum(b)
        dink = (ink_b - ink_a) / ink_a * 100 if ink_a else 0.0
        print(f"\n{case} {key}: SSIM {s:.4f}, region {region:.3f} mm², ink {dink:+.2f} %")
        if s < 0.95 or region > 0.3 or abs(dink) > 3.0:
            bad.append((key, round(s, 4), round(region, 3), round(dink, 2)))
    assert bad == [], bad


# ------------------------------------------------------------------- AC-20 ---
@pytest.mark.render
@pytest.mark.parametrize("case", ["C-4", "C-4b", "C-5"])
def test_ac20_glyph_placement(case, renders):
    import numpy as np
    page = _page600(str(renders[case]["pdf"]))
    meta = META["cases"][case]
    worst, n = (0.0, None), 0
    for col in meta["columns"]:
        crop = meta["crops"][col["key"]]
        cx0, cy0 = crop["box_px600"][:2]
        ref = _ref_img(crop["file"])
        for i, ch in enumerate(col["chars"]):
            if ch is None:
                continue
            y = col["y0"] + i * col["size"]
            half = 0.5 * col["size"]
            x0, y0, x1, y1 = refkit.box_px((col["x"] - half, y - half, col["x"] + half, y + half), 600)
            a = ref[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0].astype(float)
            b = page[y0:y1, x0:x1].astype(float)
            a, b = refkit.same_shape(a, b)
            if refkit.ink_sum(a) < 255 * 20:
                continue
            dy, dx = refkit.xcorr_offset(a, b)
            d = float(np.hypot(dy, dx) * refkit.MM / 600)
            n += 1
            if d > worst[0]:
                worst = (d, f"{col['key']} {ch}")
    print(f"\n{case}: {n} glyphs, worst {worst[1]} {worst[0]:.4f} mm")
    assert n > 10
    assert worst[0] <= 0.15, worst


@pytest.mark.render
@pytest.mark.parametrize("case", PDF_CASES)
def test_ac20_crest_ring(case, renders):
    import numpy as np
    page = _page600(str(renders[case]["pdf"]))
    meta = META["cases"][case]
    crop = meta["crops"]["crest"]
    cx0, cy0 = crop["box_px600"][:2]
    ref = _ref_img(crop["file"]).astype(float)
    R, ccx, ccy = meta["crest"]["R"], meta["crest"]["cx"], meta["crest"]["cy"]
    worst = (0.0, None)
    for ch, gx, gy in meta["ring"]:
        box = (gx - 0.16 * R, gy - 0.16 * R, gx + 0.16 * R, gy + 0.16 * R)
        x0, y0, x1, y1 = refkit.box_px(box, 600)
        a = ref[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0]
        b = page[y0:y1, x0:x1].astype(float)
        a, b = refkit.same_shape(a, b)
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        px = x0 * refkit.MM / 600 + (xx + 0.5) * refkit.MM / 600
        py = y0 * refkit.MM / 600 + (yy + 0.5) * refkit.MM / 600
        rr = np.hypot(px - ccx, py - ccy) / R
        band = (rr > 0.68) & (rr < 0.985)
        cen = []
        for im in (a, b):
            w = (255 - im) * band
            assert w.sum() > 0, f"no ink for ring glyph {ch}"
            cen.append(((w * px).sum() / w.sum(), (w * py).sum() / w.sum()))
        d = float(np.hypot(cen[0][0] - cen[1][0], cen[0][1] - cen[1][1]))
        if d > worst[0]:
            worst = (d, ch)
    print(f"\n{case} crest ring: worst {worst[1]} {worst[0]:.4f} mm")
    assert worst[0] <= 0.15, worst


# ------------------------------------------------------------------- AC-21 ---
@pytest.mark.render
@pytest.mark.parametrize("case", ["C-1", "C-3"])
def test_ac21_text_layer(case, svg_renders):
    import numpy as np
    from PIL import Image
    out = svg_renders[case]
    ref = META["cases"][case]["textlayer"]
    svg = next(p for p in out.glob("*.svg"))
    text = svg.read_text(encoding="utf-8")
    m = re.search(r'<image x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                  r'xlink:href="([^"]+-textlayer\.png)" preserveAspectRatio="none"/>', text)
    assert m, "no <image> for the text layer in its old form"
    box = [float(m.group(i)) for i in range(1, 5)]
    assert all(abs(p - q) <= 0.05 for p, q in zip(box, ref["bbox_mm"])), (box, ref["bbox_mm"])
    with Image.open(out / m.group(5)) as im:
        assert im.mode == "RGBA"
        size = im.size
        rgba = np.asarray(im)
    assert abs(size[0] - ref["size"][0]) <= 1 and abs(size[1] - ref["size"][1]) <= 1, size
    assert abs(size[0] - round(box[2] * 600 / 25.4)) <= 1
    assert abs(size[1] - round(box[3] * 600 / 25.4)) <= 1
    a_new = rgba[..., 3]
    a_ref = _ref_img(f"{case}-textlayer-graded.png")
    a_ref, a_new = refkit.same_shape(a_ref, a_new)
    ma, mb = a_ref > 128, a_new > 128
    iou = float((ma & mb).sum() / (ma | mb).sum())
    total = a_new.astype(np.int64).sum() / a_ref.astype(np.int64).sum() - 1
    print(f"\n{case} text layer: {size}, IoU {iou:.4f}, alpha {total * 100:+.2f} %")
    assert iou >= 0.98, iou
    assert abs(total) <= 0.02, total
    inked = rgba[..., 3] > 0
    assert (rgba[inked][:, :3] == 17).all()


# ------------------------------------------------------------------- AC-23 ---
def test_ac23_help_offers_todays_options(home, tmp_path):
    r = _run(["-c", EX, "--help"], home, tmp_path, COLUMNS="1000")
    assert r.returncode == 0
    longs = set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", r.stdout))
    shorts = set(re.findall(r"(?:^|[\s,\[])(-[a-z])(?=[\s,\]])", r.stdout, re.M))
    assert longs == OPTIONS, longs ^ OPTIONS
    assert shorts == SHORT, shorts ^ SHORT


@pytest.mark.render
def test_ac23_progress_before_the_file(tmp_path):
    out = tmp_path / "out"
    seen = []

    def report(event):
        ext = {"pdf": "*.pdf", "png": "*.png"}.get(event["stage"])
        exists = bool(list(out.glob(f"dan-{event['variant']}*{ext[1:]}"))) if ext else None
        seen.append((event["variant"], event["stage"], exists))

    bd.main(["-c", EX, "-a", "dan", "-v", "overlay,overlay-flat", "-f", "pdf,png",
             "--name=", "--rank=", "--date=", f"--out={out}"], progress=report)
    assert [(v, s) for v, s, _ in seen] == [
        ("overlay", "text"), ("overlay", "ink"), ("overlay", "pdf"), ("overlay", "png"),
        ("overlay-flat", "pdf"), ("overlay-flat", "png")]
    late = [(v, s) for v, s, e in seen if e]
    assert late == [], f"reported after the file was written: {late}"


# ------------------------------------------------------------------- AC-24 ---
INJECT = {
    "ellipse": ('<ellipse cx="30" cy="30" rx="5" ry="3" fill="#111111"/>', r"ellipse"),
    "use": ('<use href="#nothing" x="10" y="10"/>', r"\buse\b"),
    "style": ('<rect x="30" y="30" width="5" height="5" style="fill:#111111"/>', r"style"),
}


@pytest.mark.parametrize("kind", list(INJECT))
def test_ac24_unsupported_svg_is_refused(kind, tmp_path, monkeypatch, capsys):
    real = bd.document
    element, word = INJECT[kind]

    def document(*a, **k):
        svg = real(*a, **k)
        if k.get("layer", "all") == "text":
            return svg
        head, tail = svg.rsplit("</svg>", 1)
        return head + element + "\n</svg>" + tail

    monkeypatch.setattr(bd, "document", document)
    out = tmp_path / "out"
    code, ev, _ = _cli(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-f", "pdf,png",
                        "--name=", "--rank=", "--date=", f"--out={out}", "--json"], capsys)
    kinds = [e["event"] for e in ev]
    assert code == 1 and kinds and kinds[-1] == "error" and kinds.count("error") == 1, ev
    assert "done" not in kinds and "file" not in kinds, ev
    assert re.search(word, ev[-1]["message"] + ev[-1].get("detail", ""), re.I), ev[-1]
    assert not list(out.glob("*.pdf")) and not list(out.glob("*.png"))
    assert not (out / ".work").exists()


# ------------------------------------------------------------------- AC-26 ---
@pytest.mark.render
@pytest.mark.parametrize("case, limit_mb", [("C-1", 400), ("C-4", 160)])
def test_ac26_process_peak_guard(case, limit_mb, session_home, tmp_path):
    report = tmp_path / "peak.json"
    r = subprocess.run([sys.executable, str(KIT / "peak_driver.py"), str(report), "--",
                        "-c", EX, *refkit.CASES[case], f"--out={tmp_path / 'out'}"],
                       env=support.isolated_env(session_home), cwd=str(tmp_path),
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-1500:]
    peak = json.loads(report.read_text())["peak_rss"] / 2 ** 20
    print(f"\n{case}: menkyo process peak RSS {peak:.0f} MB (guard {limit_mb})")
    assert peak <= limit_mb


# ------------------------------------------------------------------- AC-27 ---
@pytest.mark.render
def test_ac27_time_guard(renders):
    print(f"\nC-1 wall {renders['C-1']['wall']:.1f} s, C-4 {renders['C-4']['wall']:.1f} s")
    assert renders["C-1"]["wall"] <= 60


# ------------------------------------------------------------------- AC-28 ---
@pytest.mark.slow
def test_ac28_wheel_fonts_and_size(dist):
    lic = _crest_licence()
    with zipfile.ZipFile(dist["wheel"]) as z:
        names = z.namelist()
        for f in ("YujiBoku-Regular.ttf", "NotoSerifJP-SemiBold.otf", "OFL.txt", lic.name):
            assert f"menkyo/fonts/{f}" in names, f
            assert z.read(f"menkyo/fonts/{f}") == (FONTS / f).read_bytes(), f
        meta = z.read(next(n for n in names if n.endswith(".dist-info/METADATA"))).decode()
        licences = {n.rsplit("/", 1)[-1] for n in names if "/licenses/" in n}
    reqs = re.findall(r"^Requires-Dist: (.+)$", meta, re.M)
    assert _dep_names(reqs) == DEPS, reqs
    assert lic.name in licences, licences
    size = dist["wheel"].stat().st_size
    print(f"\nwheel: {size / 1e6:.2f} MB")
    assert size <= WHEEL_MAX, size


# ------------------------------------------------------------------- AC-29 ---
@pytest.mark.slow
@pytest.mark.render
def test_ac29_installed_wheel_renders(installed, home, tmp_path):
    exe = [str(installed["menkyo"])]
    path = os.pathsep.join([str(installed["venv"] / "bin"), "/usr/bin", "/bin"])
    ex = _run(["--example-config"], home, tmp_path, exe=exe, path=path)
    (tmp_path / "example.toml").write_text(ex.stdout, encoding="utf-8")
    for case in ("C-1", "C-4"):
        out = tmp_path / f"out-{case}"
        r = _run(["-c", "example.toml", *refkit.CASES[case], f"--out={out}", "--json"],
                 home, tmp_path, exe=exe, path=path)
        assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
        ev = support.events(r.stdout)
        got = _outputs(out)
        assert ev[-1] == {"event": "done", "out": str(out),
                          "files": [str(got["pdf"]), str(got["png"])]}
        s = refkit.pdf_summary(got["pdf"])
        assert s["pages"] == 1 and refkit.xref_problems(got["pdf"]) == []
        assert s["font_objects"] == 0 and s["text_ops"] == 0
        assert set(s["colour_ops"]) <= GREY_OPS, s


# ------------------------------------------------------------------- AC-31 ---
def test_ac31_no_require_render_and_no_fakes():
    files = [support.TESTS / "conftest.py", support.TESTS / "README.md",
             support.TESTS / "docker" / "Dockerfile", support.REPO / "scripts" / "test-docker.sh",
             support.REPO / ".github" / "workflows" / "package.yml",
             support.REPO / "pyproject.toml"]
    for f in files:
        assert "REQUIRE_RENDER" not in f.read_text(encoding="utf-8"), f
    assert not (support.TESTS / "fakes").exists()
    assert not hasattr(support, "make_fake_bin") and not hasattr(support, "find_inkscape")
    conftest = (support.TESTS / "conftest.py").read_text(encoding="utf-8")
    for gone in ("def fake_tools", "def no_tools", "def inkscape", "def require_program",
                 "class FakeTools"):
        assert gone not in conftest, gone
    markers = _pyproject()["tool"]["pytest"]["ini_options"]["markers"]
    assert any(m.startswith("render:") for m in markers), markers


# ------------------------------------------------------------------- AC-32 ---
def test_ac32_test_image_is_slim():
    df = (support.TESTS / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^FROM python:3\.13-slim-bookworm\b", df, re.M)
    assert "apt-get" not in df
    for gone in ("inkscape", "poppler", "fontconfig", "fonts-noto"):
        assert gone not in df.lower(), gone
    assert "test ! -e dojo.toml" in df
    script = (support.REPO / "scripts" / "test-docker.sh").read_text(encoding="utf-8")
    assert "tests/docker/Dockerfile" in script and "pytest" in script


# ------------------------------------------------------------------- AC-33 ---
def test_ac33_workflow():
    wf = (support.REPO / ".github" / "workflows" / "package.yml").read_text(encoding="utf-8")
    for gone in ("apt-get", "pdffonts", "REQUIRE_RENDER", "inkscape", "fonts-noto"):
        assert gone not in wf, gone
    assert re.search(r"uv run --frozen pytest", wf)
    smoke = wf.split("Smoke test the installed wheel", 1)[1]
    assert re.search(r"-v overlay,overlay-flat\b", smoke)
    assert "--json" in smoke and '"event": "done"' in smoke


# ------------------------------------------------------------------- AC-34 ---
def test_ac34_readme():
    text = _readme()
    for gone in ("inkscape", "fontconfig", "apt-get", "poppler", "fonts-noto",
                 "inkscape failed"):
        assert gone not in text.lower(), gone
    assert "Noto Serif JP" in text
    looks = _section(text, "How it looks the way it does")
    assert "Yuji Boku" in looks and "Noto Serif JP" in looks
    layout = _section(text, "Layout")
    fonts_line = next(l for l in layout.splitlines() if l.strip().startswith("fonts/"))
    assert "Yuji Boku" in fonts_line and "Noto" in fonts_line, fonts_line
    package = _section(text, "As a package")
    assert re.search(r"U\+[0-9A-F]{4}|missing|replacement", package), \
        "the missing-glyph error is not described"
    assert re.search(r"outline", text, re.I) and re.search(r"search|cop(y|ied)", text, re.I)


# ------------------------------------------------------------------- AC-35 ---
def _decisions():
    return (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")


def test_ac35_history_untouched():
    old = _git("show", f"{BASELINE}:DECISIONS.md")
    if old is None:
        pytest.skip("no git history here (the Docker image)")
    kept = old.stdout.split("\n## Open\n", 1)[0]
    assert _decisions().split("\n## Open\n", 1)[0].startswith(kept), \
        "an entry up to the last one at 8509b85 changed"


def test_ac35_decisions_entry():
    entries = _decisions().split("\n## Open\n", 1)[0]
    blocks = [b for b in re.split(r"^(?=## )", entries, flags=re.M) if b.startswith("## ")]
    # Either dash: new text follows the house style (spaced en dash).  Only
    # entries newer than the baseline count: 2026-10-28's "xlink:href ... for
    # Inkscape 1.2" names Inkscape too, and must stay as it is.
    old = _git("show", f"{BASELINE}:DECISIONS.md")
    before = set(re.findall(r"^## .*$", old.stdout, re.M)) if old is not None else set()
    mine = [b for b in blocks if re.match(r"## (\d{4}-\d{2}-\d{2}) [–—] ", b)
            and re.match(r"## (\d{4}-\d{2}-\d{2})", b).group(1) >= "2026-10-29"
            and b.splitlines()[0] not in before
            and "inkscape" in b.splitlines()[0].lower()]
    assert len(mine) == 1, [b.splitlines()[0] for b in blocks[-4:]]
    body = mine[0]
    for word in ("fontTools", "pdfium", "Noto Serif JP", "DeviceGray", "outline",
                 "Noto Serif CJK JP"):          # the last: the family-name mapping
        assert word in body, word
    assert re.search(r"search|cop(y|ied)", body), "text not searchable"
    assert len(re.findall(r"\d+(?:\.\d+)?\s?MB", body)) >= 4, "the before/after figures"
    assert re.search(r"missing|lacks", body) and re.search(r"glyph|character", body)
    assert re.search(r"gr[ae]yscale", body, re.I)
    # (the second name is split: the flag-removal item's AC-11 bans the word)
    for overridden in ("The font is vendored", "Output, and the super" "sampling cap",
                       "Installed-copy behaviour", "Packaging is tested by rendering"):
        assert overridden in body, overridden


def test_ac35_open_item_closed():
    _, open_ = _decisions().split("\n## Open\n", 1)
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    assert not [i for i in items if "Inkscape" in i], items
    for kept in ("Paper format", "Kyū grades", "An annotated version in Dutch"):
        assert [i for i in items if i.startswith(kept)], (kept, items)
    # the user decided 2026-10-29: the existing docs get a house-style sweep
    assert [i for i in items if re.search(r"house.style", i, re.I)], items


# ------------------------------------------------------------------- AC-36 ---
def test_ac36_tests_readme_and_marker():
    readme = (support.TESTS / "README.md").read_text(encoding="utf-8")
    for gone in ("REQUIRE_RENDER", "fake_tool", "stand-in"):
        assert gone not in readme, gone
    assert "render_without_inkscape" in readme
    assert re.search(r"--ref", readme)
    markers = _pyproject()["tool"]["pytest"]["ini_options"]["markers"]
    render = next(m for m in markers if m.startswith("render:"))
    assert "inkscape" not in render.lower(), render


# ------------------------------------------------------------------- AC-37 ---
def test_ac37_version(home, tmp_path):
    assert support.project_version() == EXPECTED_VERSION
    r = _run(["--version"], home, tmp_path)
    assert (r.returncode, r.stdout) == (0, f"menkyo {EXPECTED_VERSION}\n")
