"""kyu-grades: a kyū certificate, a new award `kyu` on a simpler sheet (no
crest, no crest ring, no motto), and --rank that counts in the award's own
unit: on a kyū award `-r 5`, `gokyu` or `yellow` is 五級 and `white-yellow`
or `jun5` is 準五級; on a dan award `-r 5` stays 五段.

Contract: docs/work/kyu-grades/acceptance.md.  The user's decisions of
2026-10-29 are not reopened here; where the contract follows a
recommendation still open (OQ-n), the test says so, and the constants below
are where a different answer is changed.

Every run passes -c with the shipped example or a configuration written
here, and HOME / XDG_CONFIG_HOME are isolated (conftest, support).
"""

import math
import os
import re
import sys
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod

sys.path.insert(0, str(support.TESTS / "regression"))
import golden_lib  # noqa: E402
from golden_cases import CASES  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import house_style  # noqa: E402

EX = str(support.EXAMPLE)
S = 1 / math.sqrt(2)
PLAIN = ["overlay", "overlay-flat", "proof"]
DATE = "2026-09-05"
DATE_KANJI = "西暦二〇二六年九月五日"

# OQ-5: the example's awards, kyu appended after the three it had.
AWARDS = ["dan", "shihan", "renshi", "kyu"]

# User decision 2: the example's kyū heading and formula.
KYU_HEADING, KYU_FORMULA = "級位認定証", "右認定ス"

# OQ-1: an award declares its unit with grade_column, which keeps true
# (= "dan") and false, and takes "dan" or "kyu".
UNIT_KEY = "grade_column"
# OQ-2: the simpler sheet is two keys per award, both true by default.
CREST_KEY, MOTTO_KEY = "crest", "motto"

KYU = {1: "一級", 2: "二級", 3: "三級", 4: "四級", 5: "五級",
       6: "六級", 7: "七級", 8: "八級", 9: "九級", 10: "十級"}

# The example's own stand-ins, which a kyū sheet still prints.
ART, DOJO, TITLE, SIGNER, MOTTO = "〇〇流柔術", "〇〇道場", "師範", "山田太郎", "柔能制剛"

NAME = "ヤン・ヤンセン"


# ----------------------------------------------------------------- helpers ----
def _example():
    return support.EXAMPLE.read_text(encoding="utf-8")


def _blocks(text):
    """[(start, end)] line ranges of each table, header to next header."""
    lines = text.splitlines(keepends=True)
    heads = [i for i, l in enumerate(lines) if re.match(r"^\s*\[", l)] + [len(lines)]
    return lines, list(zip(heads, heads[1:]))


def award_block(text, slug):
    """The [[awards]] block of `slug` in a configuration, as text."""
    lines, spans = _blocks(text)
    for start, end in spans:
        block = "".join(lines[start:end])
        if lines[start].strip() == "[[awards]]" and re.search(
                rf'^\s*slug\s*=\s*"{re.escape(slug)}"', block, re.M):
            return block
    raise AssertionError(f"no [[awards]] block for {slug!r}")


def with_award(text, slug, edit):
    """`text` with `slug`'s [[awards]] block replaced by edit(block)."""
    block = award_block(text, slug)
    return text.replace(block, edit(block), 1)


def set_key(block, key, value):
    """`block` with `key = value` (a TOML literal), replacing the key if the
    block has it, else added after the slug."""
    pat = re.compile(rf"^\s*{key}\s*=.*$", re.M)
    if pat.search(block):
        return pat.sub(f"{key} = {value}", block, count=1)
    return re.sub(r'^(\s*slug\s*=.*)$', rf"\1\n{key} = {value}", block, count=1, flags=re.M)


def write_config(tmp_path, text, name="kyu.toml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def run(args, home, tmp_path, exe=None, **env):
    return support.run_menkyo([str(a) for a in args], support.isolated_env(home, **env),
                              tmp_path, exe=exe)


def listing(args, home, tmp_path, config=EX):
    r = run(["-c", config, "--list", *args, f"--out={tmp_path / 'o'}"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "o").exists()
    return r.stdout.splitlines()


def svgs(args, tmp_path, config=EX, variant="overlay-flat", out="svg"):
    """Run main() in-process with -f svg --no-ink; {award: svg text}."""
    o = tmp_path / out
    bd.main(["-c", config, "-v", variant, "-f", "svg", "--no-ink", "--suffix", "t",
             *args, f"--out={o}"])
    got = {}
    for p in sorted(o.glob(f"*-{variant}-*-t.svg")):
        got[p.name.split(f"-{variant}-")[0]] = p.read_text(encoding="utf-8")
    return got


def svg_of(slug, args, tmp_path, **kw):
    return svgs(["-a", slug, *args], tmp_path, **kw)[slug]


def fails(args, config=EX, tmp_path=None):
    """main()'s SystemExit message for a run that must fail."""
    out = ["--out", str(tmp_path / "fail")] if tmp_path else []
    with pytest.raises(SystemExit) as e:
        bd.main(["-c", config, "-v", "overlay-flat", "-f", "svg", *args, *out])
    assert isinstance(e.value.code, str), e.value.code
    if tmp_path:
        assert not (tmp_path / "fail").exists() or not any((tmp_path / "fail").iterdir())
    return e.value.code


_TEXT = re.compile(r'<text x="([-\d.]+)" y="([-\d.]+)" font-family="([^"]+)" '
                   r'font-weight="(\d+)" font-size="([\d.]+)"([^>]*)>(.*?)</text>')


def texts(svg, family=None):
    """Every <text> as (x, y, family, weight, size, extra, char)."""
    out = [(float(m[1]), float(m[2]), m[3], m[4], float(m[5]), m[6], m[7])
           for m in _TEXT.finditer(svg)]
    return [t for t in out if family is None or t[2] == family]


def body(svg):
    return texts(svg, bd.FONT_BODY)


def column(svg, x, tol=4.0):
    """The body-font characters within `tol` mm of x, top down."""
    return "".join(t[6] for t in sorted((t for t in body(svg) if abs(t[0] - x) <= tol),
                                        key=lambda t: t[1]))


def columns(svg):
    """Every body-font column, keyed by its x rounded to the mm."""
    cols = {}
    for t in sorted(body(svg), key=lambda t: t[1]):
        cols.setdefault(round(t[0]), []).append(t[6])
    return {x: "".join(c) for x, c in cols.items()}


def printed_rank(svg):
    """The grade printed with no name on the sheet: the column at X_RANK."""
    return column(svg, bd.X_RANK, tol=16.0)


def kyu_rank(value, tmp_path, slug="kyu", config=EX):
    svg = svg_of(slug, ["-n", "", "-d", "", "-r", value], tmp_path, config=config)
    return printed_rank(svg)


def y_rank():
    return bd.Y_RANK + 0.05 * bd.PAGE_H         # the example's text_drop


def crest_parts(svg):
    """What the crest draws: its rings, the mon, the ring lettering."""
    return {"circles": len(re.findall(r'<circle r="', svg)),
            "mon": svg.count('fill-rule="evenodd"'),
            "ring": len(texts(svg, bd.FONT_CREST))}


def _tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()} if root.exists() else {}


# ------------------------------------------------------------------- AC-1 ----
def test_ac1_example_has_the_kyu_award():
    c = config_mod.load(EX)
    assert c.slugs == AWARDS                                    # OQ-5: appended
    kyu = c.award("kyu")
    assert (kyu.heading, kyu.formula) == (KYU_HEADING, KYU_FORMULA)
    block = award_block(_example(), "kyu")
    assert re.search(rf'^\s*{UNIT_KEY}\s*=\s*"kyu"', block, re.M), block       # OQ-1
    assert re.search(rf"^\s*{CREST_KEY}\s*=\s*false", block, re.M), block      # OQ-2
    assert re.search(rf"^\s*{MOTTO_KEY}\s*=\s*false", block, re.M), block      # OQ-2
    # the three that were there are untouched in what they say
    for slug, heading, formula in (("dan", "段位免状", "右授与ス"),
                                   ("shihan", "師範免許状", "右免許ス"),
                                   ("renshi", "錬士免許状", "右免許ス")):
        a = c.award(slug)
        assert (a.heading, a.formula) == (heading, formula)


def test_ac1_example_config_prints_it(home, tmp_path):
    r = run(["--example-config"], home, tmp_path)
    assert r.returncode == 0
    assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()
    assert 'slug = "kyu"' in r.stdout and KYU_HEADING in r.stdout


def test_ac1_help_lists_kyu(home, tmp_path):
    r = run(["-c", EX, "--help"], home, tmp_path, COLUMNS="1000")
    assert r.returncode == 0, r.stderr
    assert "comma-separated: dan,shihan,renshi,kyu (default: all)" in r.stdout
    # the --rank help says what a kyū award takes
    # "-r GRADE, --rank GRADE" up to Python 3.12, "-r, --rank GRADE" from 3.13
    rank_help = re.split(r"-r(?: GRADE)?, --rank GRADE", r.stdout, maxsplit=1)[1] \
        .split("\n  -", 1)[0]
    assert re.search(r"ky[uū]", rank_help, re.I), rank_help
    assert "級" in rank_help, rank_help


# ------------------------------------------------------------------- AC-2 ----
def test_ac2_default_and_all_include_kyu(home, tmp_path):
    assert listing([], home, tmp_path) == [f"{a}-overlay-a3-sample.pdf" for a in AWARDS]
    assert listing(["--all"], home, tmp_path) == [
        f"{a}-{v}-a3-sample.pdf" for a in AWARDS for v in PLAIN]
    assert listing(["-a", "all", "--paper", "a4"], home, tmp_path) == [
        f"{a}-overlay-a4-sample.pdf" for a in AWARDS]


NAME_CASES = [
    (["-a", "kyu"], ["kyu-overlay-a3-sample.pdf"]),
    (["-a", "kyu", "--paper", "a4"], ["kyu-overlay-a4-sample.pdf"]),
    (["-a", "kyu", "-v", "all", "-f", "pdf,png"],
     [f"kyu-{v}-a3-sample.{e}" for v in PLAIN for e in ("pdf", "png")]),
    (["-a", "kyu", "-r", "yellow", "-n", NAME], ["kyu-overlay-a3-yellow-ヤン-ヤンセン.pdf"]),
    (["-a", "kyu", "-r", "white-yellow"], ["kyu-overlay-a3-white-yellow.pdf"]),
    (["-a", "kyu", "-r", "5"], ["kyu-overlay-a3-5.pdf"]),
    (["-a", "kyu", "-r", "準五級", "--paper", "a4"], ["kyu-overlay-a4-準五級.pdf"]),
    (["-a", "kyu", "--suffix", ""], ["kyu-overlay-a3.pdf"]),
    (["-a", "dan,kyu", "-r", "3"], ["dan-overlay-a3-3.pdf", "kyu-overlay-a3-3.pdf"]),
]


@pytest.mark.parametrize("args, names", NAME_CASES, ids=[" ".join(c[0]) for c in NAME_CASES])
def test_ac2_names(args, names, home, tmp_path):
    assert listing(args, home, tmp_path) == names


def test_ac2_planned_events(home, tmp_path):
    r = run(["-c", EX, "--list", "--json", "-a", "kyu", "-v", "all"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert support.events(r.stdout) == [
        {"event": "planned", "file": f"kyu-{v}-a3-sample.pdf"} for v in PLAIN]


# ------------------------------------------------------------------- AC-3 ----
@pytest.mark.parametrize("variant", ["overlay-flat", "proof"])
def test_ac3_no_crest_no_ring_no_motto(variant, tmp_path):
    args = ["-a", "dan,kyu", "-n", NAME, "-r", "5", "-d", DATE]
    got = svgs(args, tmp_path, variant=variant)
    dan, kyu = got["dan"], got["kyu"]
    # not vacuous: the dan sheet has every one of them
    assert crest_parts(dan)["mon"] == 1 and crest_parts(dan)["ring"] > 0
    assert column(dan, bd.X_MOTTO) == MOTTO
    parts = crest_parts(kyu)
    assert parts["mon"] == 0 and parts["ring"] == 0, parts
    # the only circle a kyū sheet may have is the proof's seal guide
    circles = re.findall(r"<circle [^>]*>", kyu)
    if variant == "proof":
        assert len(circles) == 1 and f'r="{bd.SEAL_R}"' in circles[0], circles
    else:
        assert circles == []
    assert bd.FONT_CREST not in kyu
    assert column(kyu, bd.X_MOTTO, tol=8.0) == ""
    assert MOTTO not in "".join(columns(kyu).values())


def test_ac3_keeps_the_core_text(tmp_path):
    kyu = svg_of("kyu", ["-n", NAME, "-r", "5", "-d", DATE], tmp_path)
    cols = set(columns(kyu).values())
    for want in (KYU_HEADING, NAME + "殿", "五級", KYU_FORMULA, DATE_KANJI,
                 ART, DOJO, TITLE, SIGNER):
        assert want in cols, (want, cols)
    assert cols == {KYU_HEADING, NAME + "殿", "五級", KYU_FORMULA, DATE_KANJI,
                    ART, DOJO, TITLE, SIGNER}, cols


def test_ac3_blank_slots_stay_blank(tmp_path):
    kyu = svg_of("kyu", ["-n", "", "-r", "", "-d", ""], tmp_path)
    cols = set(columns(kyu).values())
    assert cols == {KYU_HEADING, KYU_FORMULA, "西暦年月日", ART, DOJO, TITLE, SIGNER}, cols


# ------------------------------------------------------------------- AC-4 ----
# OQ-3, the user's decision (option B): on an award with `motto = false`
# every column, and the seal, moves SHIFT mm left, so the printed block is
# centred on the sheet (about 69 mm each side).  Keyed on the award's motto
# key, never on an empty [motto] text.  The crest's place stays empty.
SHIFT = 10.0


def shift_of(slug):
    """How far left an award's columns sit, in the example (kyu: motto = false)."""
    return SHIFT if slug == "kyu" else 0.0


def _split(svg, x_rank, dx=0.0):
    """(heading, formula, rank, motto, the rest) of a sheet's body text, its
    columns `dx` mm left of the dan sheet's."""
    parts = {"heading": [], "formula": [], "rank": [], "motto": [], "rest": []}
    for t in body(svg):
        x = t[0] + dx
        if abs(x - bd.X_HEADING) < 0.01:
            parts["heading"].append(t)
        elif abs(x - bd.X_VERB) < 0.01:
            parts["formula"].append(t)
        elif abs(x - x_rank) < 0.01:
            parts["rank"].append(t)
        elif abs(x - bd.X_MOTTO) < 0.01:
            parts["motto"].append(t)
        else:
            parts["rest"].append(t)
    return parts


def _placed(ts, dx=0.0):
    """Text elements as comparable tuples, moved `dx` mm right; the rotate
    attribute (which repeats x) is left out."""
    return sorted((round(t[0] + dx, 3), t[1], t[2], t[3], t[4], t[6]) for t in ts)


@pytest.mark.parametrize("args", [
    ["-n", NAME, "-r", "5", "-d", DATE],
    ["-n", "", "-r", "5", "-d", ""],
    ["-n", NAME, "-r", "", "-d", DATE],
    ["-n", "", "-r", "", "-d", ""],
], ids=["filled", "grade-only", "name-date", "blank"])
@pytest.mark.parametrize("paper", ["a3", "a4"])
def test_ac4_same_columns_as_the_dan_sheet_moved_left(args, paper, tmp_path):
    got = svgs(["-a", "dan,kyu", "--paper", paper, *args], tmp_path)
    named = args[1] != ""
    x_rank = bd.right_columns(True)[1] if named else bd.X_RANK
    dan, kyu = _split(got["dan"], x_rank), _split(got["kyu"], x_rank, SHIFT)
    # name, date, art, dōjō, office and signatory: the dan sheet's glyphs,
    # SHIFT mm to the left, the same height and size
    assert _placed(kyu["rest"], SHIFT) == _placed(dan["rest"])
    assert kyu["motto"] == []
    # heading and formula start where the dan sheet's do, SHIFT mm left
    for part in ("heading", "formula"):
        d, k = sorted(dan[part], key=lambda t: t[1]), sorted(kyu[part], key=lambda t: t[1])
        assert k and (round(k[0][0] + SHIFT, 3), k[0][1], k[0][4]) == \
            (d[0][0], d[0][1], d[0][4]), part
    # the grade sits in the dan sheet's grade column, SHIFT mm left
    assert bool(kyu["rank"]) == bool(dan["rank"])
    if paper == "a4":
        assert '<g transform="scale(0.7071067812)">' in got["kyu"]


def test_ac4_kyu_block_is_centred(tmp_path):
    """Option B's point: the printed block's margins agree within 1 mm."""
    kyu = svg_of("kyu", ["-n", NAME, "-r", "5", "-d", DATE], tmp_path)
    left = min(t[0] - t[4] / 2 for t in body(kyu))
    right = max(t[0] + t[4] / 2 for t in body(kyu))
    assert abs(left - (bd.PAGE_W - right)) < 1.0, (left, bd.PAGE_W - right)
    assert left == pytest.approx(bd.X_SIGNER - SHIFT - bd.SZ_SIGNER / 2, abs=0.01)


def test_ac4_an_empty_precept_moves_nothing(tmp_path):
    """The move hangs off the award's motto key: a dōjō without a precept
    (`[motto] text = ""`) keeps every dan column where it was."""
    text = _example().replace('text = "柔能制剛"', 'text = ""')
    assert 'text = ""' in text
    cfg = write_config(tmp_path, text)
    args = ["-n", NAME, "-r", "5", "-d", DATE]
    a = svg_of("dan", args, tmp_path, out="a")
    b = svg_of("dan", args, tmp_path, config=cfg, out="b")
    motto = [l for l in a.splitlines() if f'<text x="{bd.X_MOTTO:.3f}"' in l]
    assert len(motto) == len(MOTTO)
    # an empty column leaves an empty line, as it always has (the
    # minimal.toml goldens have it): blank lines are not compared
    assert [l for l in b.splitlines() if l] == \
        [l for l in a.splitlines() if l and l not in motto]


# OQ-12, agreed rule (Agreement 4): size = min(SZ_RANK, 2 * SZ_RANK / n),
# top-aligned, the first glyph's top at y_rank - SZ_RANK / 2, so the column
# never exceeds the two-character extent of 60 mm.  On every award.
@pytest.mark.parametrize("slug, value, grade", [
    ("kyu", "white-yellow", "準五級"), ("kyu", "5", "五級"), ("kyu", "10", "十級"),
    ("kyu", "三級", "三級"), ("dan", "Shihan", "Shihan"), ("dan", "2", "二段"),
    ("shihan", "師範代", "師範代")])
@pytest.mark.parametrize("name", ["", NAME])
def test_ac4_grade_stays_in_its_zone(slug, value, grade, name, tmp_path):
    svg = svg_of(slug, ["-n", name, "-r", value, "-d", ""], tmp_path)
    x_rank = bd.right_columns(True)[1] if name else bd.X_RANK
    rank = sorted(_split(svg, x_rank, shift_of(slug))["rank"], key=lambda t: t[1])
    assert "".join(t[6] for t in rank) == grade
    n = len(grade)
    want = min(bd.SZ_RANK, 2 * bd.SZ_RANK / n)
    top = y_rank() - bd.SZ_RANK / 2
    for i, (x, y, _f, _w, size, _e, ch) in enumerate(rank):
        assert size == pytest.approx(want, abs=0.001), (ch, size)
        centre = y - bd.BASELINE_DROP * size
        assert centre == pytest.approx(top + want / 2 + i * want, abs=0.002), (ch, i)
    assert top + n * want <= y_rank() + 1.5 * bd.SZ_RANK + 0.01


# ------------------------------------------------------------------- AC-5 ----
A3_PT = (420 * 72 / 25.4, 297 * 72 / 25.4)
A4_PT = (297 * 72 / 25.4, 210 * 72 / 25.4)


def page_size_pt(pdf):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return tuple(doc[0].get_size())
    finally:
        doc.close()


def _alpha_in(png, box_mm, scale, dpi):
    """Whether anything is drawn inside box_mm (x0, y0, x1, y1, A3 layout
    mm) of a PNG drawn at `dpi` of a sheet at `scale`."""
    from PIL import Image
    k = dpi / 25.4 * scale
    with Image.open(png) as im:
        a = im.getchannel("A")
        crop = a.crop(tuple(round(v * k) for v in box_mm))
        return crop.getbbox() is not None


# The mon and the inner part of the ring: clear of the formula, which on the
# kyū sheet moves SHIFT mm left towards the crest's place (OQ-3 B).
# It starts below y 39 mm: the proof's safe-inset guide runs along y 38.
CREST_BOX = (bd.CREST_C[0] - 18, 39.0, bd.CREST_C[0] + 10, bd.CREST_C[1] + 13)
MOTTO_BOX = (bd.X_MOTTO - 7, 95.0, bd.X_MOTTO + 7, 165.0)


@pytest.mark.render
@pytest.mark.parametrize("paper", ["a3", "a4"])
def test_ac5_renders_every_variant(paper, home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan,kyu", "-v", "all", "-f", "pdf,png", "--dpi", "50",
             "--paper", paper, "-d", DATE, f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    ev = support.events(r.stdout)
    assert ev[-1]["event"] == "done"
    want = [str(out / f"{a}-{v}-{paper}-sample.{e}") for a in ("dan", "kyu")
            for v in PLAIN for e in ("pdf", "png")]
    assert ev[-1]["files"] == want
    scale = 1.0 if paper == "a3" else S
    for v in PLAIN:
        pdf = out / f"kyu-{v}-{paper}-sample.pdf"
        assert page_size_pt(pdf) == pytest.approx(A3_PT if paper == "a3" else A4_PT, abs=0.01)
        dan_png, kyu_png = (out / f"{a}-{v}-{paper}-sample.png" for a in ("dan", "kyu"))
        # the crest's place and the motto's strip: drawn on dan, empty on kyū
        assert _alpha_in(dan_png, CREST_BOX, scale, 50), v
        assert _alpha_in(dan_png, MOTTO_BOX, scale, 50), v
        assert not _alpha_in(kyu_png, CREST_BOX, scale, 50), v
        assert not _alpha_in(kyu_png, MOTTO_BOX, scale, 50), v
        # and the heading is there
        # and the heading is there, SHIFT mm left of the dan sheet's
        heading = (bd.X_HEADING - SHIFT - 10, 70.0, bd.X_HEADING - SHIFT + 10, 170.0)
        assert _alpha_in(kyu_png, heading, scale, 50), v
        # the dan sheet's signatory column: the kyū one has moved out of it
        signer = (bd.X_SIGNER + 3, 100.0, bd.X_SIGNER + 7, 160.0)
        assert _alpha_in(dan_png, signer, scale, 50), v
        assert not _alpha_in(kyu_png, signer, scale, 50), v


@pytest.mark.render
def test_ac5_inked_svg_has_no_crest(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-v", "overlay", "-f", "svg", "-d", DATE,
             f"--out={out}"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    svg = (out / "kyu-overlay-a3-sample.svg").read_text(encoding="utf-8")
    assert 'xlink:href="kyu-overlay-a3-sample-textlayer.png"' in svg
    assert (out / "kyu-overlay-a3-sample-textlayer.png").is_file()
    assert crest_parts(svg) == {"circles": 0, "mon": 0, "ring": 0}
    assert "<circle" not in svg


@pytest.mark.render
@pytest.mark.parametrize("value", ["white-yellow", "yellow-orange", "orange-green", "10"])
def test_ac5_every_grade_form_renders(value, home, tmp_path):
    """準 and every kyū numeral go through the font and the ink."""
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-r", value, "-d", DATE, "--suffix", "t",
             f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
    assert (out / "kyu-overlay-a3-t.pdf").is_file()


# ------------------------------------------------------------------- AC-6 ----
_GUIDE = re.compile(r'<(?:rect|circle) [^>]*stroke="#(?:d8c9a8|cddbe8|e4b9b9)"[^>]*/>')


def _guides(svg, dx=0.0):
    """The proof's guides as (tag, attributes), numbers as floats; the
    calligrapher's zones and the seal moved `dx` mm right (the sheet's
    border and safe inset are the page's and never move)."""
    out = []
    for g in _GUIDE.findall(svg):
        tag = g[1:g.index(" ")]
        attrs = dict(re.findall(r'(\S+)="([^"]*)"', g))
        for k, v in attrs.items():
            try:
                attrs[k] = float(v)
            except ValueError:
                pass
        if attrs["stroke"] == "#e4b9b9":
            key = "cx" if tag == "circle" else "x"
            attrs[key] = round(attrs[key] + dx, 2)
        out.append((tag, attrs))
    return out


@pytest.mark.parametrize("args", [
    ["-n", "", "-r", "", "-d", ""],
    ["-n", NAME, "-r", "", "-d", ""],
    ["-n", "", "-r", "5", "-d", DATE],
    ["-n", NAME, "-r", "5", "-d", DATE],
], ids=["blank", "name", "rank-date", "filled"])
@pytest.mark.parametrize("paper", ["a3", "a4"])
def test_ac6_proof_guides(args, paper, tmp_path):
    got = svgs(["-a", "dan,kyu", "--paper", paper, *args], tmp_path, variant="proof")
    dan, kyu = _GUIDE.findall(got["dan"]), _GUIDE.findall(got["kyu"])
    # OQ-3 B: the same guides, the zones and the seal SHIFT mm left
    assert kyu and _guides(got["kyu"], SHIFT) == _guides(got["dan"])
    seal = [g for t, g in _guides(got["kyu"]) if t == "circle"]
    assert seal and seal[0]["cx"] == pytest.approx(bd.SEAL_C[0] - SHIFT)
    # the margins, the seal, and the calligrapher's zones for what is blank
    assert sum('stroke="#d8c9a8"' in g for g in kyu) == 1
    assert sum('stroke="#cddbe8"' in g for g in kyu) == 1
    assert sum(g.startswith("<circle") for g in kyu) == 1
    rank_zone = [g for g in kyu if 'width="32"' in g]
    assert len(rank_zone) == (1 if args[3] == "" else 0)
    name_zone = [g for g in kyu if 'width="50"' in g]
    assert len(name_zone) == (1 if args[1] == "" else 0)
    slots = [g for g in kyu if 'stroke-width="0.3"' in g]
    assert len(slots) == (9 if args[5] == "" else 0)


# ------------------------------------------------------------------- AC-7 ----
RANKS = (
    [(str(n), KYU[n]) for n in range(1, 11)]
    + [(" 5 ", "五級")]
    + [("ikkyu", KYU[1]), ("nikyu", KYU[2]), ("sankyu", KYU[3]), ("yonkyu", KYU[4]),
       ("gokyu", KYU[5]), ("rokkyu", KYU[6]), ("nanakyu", KYU[7]), ("shichikyu", KYU[7]),
       ("hachikyu", KYU[8]), ("hakkyu", KYU[8]), ("kyukyu", KYU[9]), ("jukkyu", KYU[10]),
       ("jikkyu", KYU[10])]
    + [("GoKyu", "五級"), ("gokyū", "五級"), ("gokyuu", "五級"), ("GOKYŪ", "五級"),
       (" rokkyū ", "六級")]          # OQ-7; trim, fold ū/Ū and uu, then classify
    + [("white", "六級"), ("yellow", "五級"), ("orange", "四級"), ("green", "三級"),
       ("blue", "二級"), ("brown", "一級"), ("Yellow", "五級"), ("BROWN", "一級")]
    + [("white-yellow", "準五級"), ("yellow-orange", "準四級"),
       ("orange-green", "準三級"), ("White-Yellow", "準五級")]
    + [("jun5", "準五級"), ("jun4", "準四級"), ("jun3", "準三級"), ("JUN5", "準五級"),
       ("jun-5", "準五級")]                                                  # OQ-7
    + [("三級", "三級"), ("準五級", "準五級"), ("一級", "一級"), ("弐級", "弐級"),
       ("初級", "初級")]
    # user decision 2026-10-29: full-width digits are numbers, as on dan
    + [("５", "五級"), ("１０", "十級")]
    # review R-2: NFC first, so a decomposed ū folds like a composed one
    + [("go" + "ky" + "u\u0304", "五級"), ("GOKYU\u0304", "五級")]
)


@pytest.mark.parametrize("value, grade", RANKS, ids=[r[0] for r in RANKS])
def test_ac7_kyu_rank_forms(value, grade, tmp_path):
    assert kyu_rank(value, tmp_path) == grade


# ------------------------------------------------------------------- AC-8 ----
BAD = ["purple", "red", "black", "white-orange", "green-blue", "0", "11", "99", "-1",
       "jun6", "jun2", "jun1", "jun10", "jun", "nidan", "shodan", "godan", "kyu",
       "5kyu"]                                                                # OQ-7
FORMS = ["white", "yellow", "orange", "green", "blue", "brown",
         "white-yellow", "yellow-orange", "orange-green", "jun5", "10"]


@pytest.mark.parametrize("value", BAD)
def test_ac8_unknown_kyu_rank_names_the_forms(value, tmp_path):
    msg = fails(["-a", "kyu", "-r", value], tmp_path=tmp_path)
    assert f"--rank {value}" in msg, msg
    for form in FORMS:
        assert form in msg, (form, msg)
    assert re.search(r"ky[uū]", msg, re.I), msg
    assert "Traceback" not in msg


def test_ac8_plain_error(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-r", "purple", f"--out={out}"], home, tmp_path)
    assert r.returncode != 0
    assert "--rank purple" in r.stderr and "white-yellow" in r.stderr
    assert "Traceback" not in r.stderr
    assert not out.exists()


def test_ac8_list_checks_too(home, tmp_path):
    r = run(["-c", EX, "--list", "-a", "kyu", "-r", "purple"], home, tmp_path)
    assert r.returncode != 0 and r.stdout == ""
    assert "--rank purple" in r.stderr


def test_ac8_json_error(home, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "earlier.pdf").write_bytes(b"%PDF-1.4 an earlier certificate")
    before = _tree(out)
    for extra in ([], ["--list"], ["--clean"]):
        r = run(["-c", EX, "-a", "kyu", "--rank=jun6", f"--out={out}", "--json", *extra],
                home, tmp_path)
        assert r.returncode == 1, extra
        ev = support.events(r.stdout)
        assert [e["event"] for e in ev] == ["error"], (extra, ev)
        assert "--rank jun6" in ev[0]["message"] and "jun5" in ev[0]["message"]
        assert _tree(out) == before, extra


# ------------------------------------------------------------------- AC-9 ----
DAN = [("1", "初段"), ("3", "三段"), ("10", "十段"), ("nidan", "二段"), ("SanDan", "三段"),
       ("弐段", "弐段"), ("師範", "師範"), ("Shihan", "Shihan"),
       # Agreement 5: the kyū romaji detector matches whole words
       ("kyudan", "九段"), ("kudan", "九段"),
       # OQ-13 (recommended, with the user): ū and uu fold on dan as on kyū
       ("jūdan", "十段"), ("JŪDAN", "十段"), ("kyūdan", "九段"),
       # review R-2: decomposed (NFD) ū, normalised to NFC first
       ("ju\u0304dan", "十段"), ("５", "五段")]


@pytest.mark.parametrize("value, grade", DAN, ids=[d[0] for d in DAN])
def test_ac9_dan_sheet_unchanged(value, grade, tmp_path):
    assert kyu_rank(value, tmp_path, slug="dan") == grade


def test_ac9_dan_range_message_unchanged(tmp_path):
    assert fails(["-a", "dan", "-r", "11"], tmp_path=tmp_path) == \
        "--rank 11: dan grades run from 1 to 10"


def test_ac9_licence_takes_an_explicit_rank_as_before(tmp_path):
    shihan = svg_of("shihan", ["-n", "", "-d", "", "-r", "5"], tmp_path)
    assert printed_rank(shihan) == "五段"


def test_ac9_mixed_run_each_in_its_unit(tmp_path):
    got = svgs(["-a", "dan,kyu", "-n", "", "-d", "", "-r", "3"], tmp_path)
    assert printed_rank(got["dan"]) == "三段"
    assert printed_rank(got["kyu"]) == "三級"


# OQ-4, recommended: a kyū form on a dan-unit award is refused, not printed
# as Latin text; and a dan form on a kyū award likewise (AC-8's nidan).
@pytest.mark.parametrize("slug", ["dan", "shihan"])
@pytest.mark.parametrize("value", ["yellow", "white-yellow", "jun5", "gokyu"])
def test_ac9_kyu_forms_refused_on_a_dan_award(slug, value, tmp_path):
    msg = fails(["-a", slug, "-r", value], tmp_path=tmp_path)
    assert f"--rank {value}" in msg, msg
    assert slug in msg, msg


def test_ac9_mixed_run_refused_before_anything_is_written(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan,kyu", "-v", "overlay-flat", "-r", "yellow",
             f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    assert [e["event"] for e in support.events(r.stdout)] == ["error"]
    assert not out.exists()


# ------------------------------------------------------------------ AC-10 ----
def test_ac10_sample_rank_on_a_kyu_sheet(tmp_path):
    got = svgs(["-a", "dan,shihan,kyu", "-n", "", "-d", ""], tmp_path)
    assert printed_rank(got["kyu"]) == "五級"
    assert printed_rank(got["dan"]) == "五段"
    assert printed_rank(got["shihan"]) == ""


def test_ac10_sample_rank_cleared(tmp_path):
    kyu = svg_of("kyu", ["-n", "", "-d", "", "-r", ""], tmp_path, variant="proof")
    assert printed_rank(kyu) == ""
    assert len([g for g in _GUIDE.findall(kyu) if 'width="32"' in g]) == 1


# OQ-6, recommended: the sample is read in each award's unit, and one that
# is not a grade there is an error naming [sample] rank.
def test_ac10_sample_not_drawn_not_validated(tmp_path):
    """Agreement 2: a licence draws no sample grade, so a sample that is not
    a dan grade does not stop it; an explicit --rank yellow still does."""
    text = _example().replace('rank = "5"', 'rank = "yellow"')
    cfg = write_config(tmp_path, text)
    shihan = svg_of("shihan", ["-n", "", "-d", ""], tmp_path, config=cfg)
    assert printed_rank(shihan) == ""
    msg = fails(["-a", "shihan", "-r", "yellow"], config=cfg, tmp_path=tmp_path)
    assert "--rank yellow" in msg and "shihan" in msg, msg


def test_ac10_sample_rank_in_the_kyu_unit(tmp_path):
    text = _example().replace('rank = "5"', 'rank = "yellow"')
    assert 'rank = "yellow"' in text
    cfg = write_config(tmp_path, text)
    assert printed_rank(svg_of("kyu", ["-n", "", "-d", ""], tmp_path, config=cfg)) == "五級"
    msg = fails(["-a", "dan", "-n", "", "-d", ""], config=cfg, tmp_path=tmp_path)
    assert "[sample] rank" in msg, msg


# ------------------------------------------------------------------ AC-11 ----
def test_ac11_unit_follows_the_key_not_the_slug(home, tmp_path):
    # a kyū award under another slug counts in kyū
    text = with_award(_example(), "kyu", lambda b: b.replace('slug = "kyu"',
                                                             'slug = "mudansha"'))
    cfg = write_config(tmp_path, text, "mudansha.toml")
    assert kyu_rank("5", tmp_path, slug="mudansha", config=cfg) == "五級"
    assert listing(["-a", "mudansha"], home, tmp_path, config=cfg) == \
        ["mudansha-overlay-a3-sample.pdf"]
    # and an award called kyu that declares dan counts in dan
    text = with_award(_example(), "kyu", lambda b: set_key(b, UNIT_KEY, "true"))
    cfg = write_config(tmp_path, text, "dan-unit.toml")
    assert kyu_rank("5", tmp_path, config=cfg) == "五段"


def test_ac11_true_is_dan(tmp_path):
    text = with_award(_example(), "dan", lambda b: set_key(b, UNIT_KEY, '"dan"'))
    cfg = write_config(tmp_path, text)
    for args in (["-n", NAME, "-r", "2", "-d", DATE], ["-n", "", "-r", "", "-d", ""]):
        a = svg_of("dan", args, tmp_path, out="a")
        b = svg_of("dan", args, tmp_path, config=cfg, out="b")
        assert a == b


def test_ac11_licences_unchanged_by_false(tmp_path):
    """grade_column = false still means no grade column, sample or not."""
    # without a name: printed_rank() reads the column around X_RANK, where
    # a licence's name sits (308 mm) when there is one
    assert printed_rank(svg_of("shihan", ["-n", "", "-d", DATE], tmp_path, out="a")) == ""
    shihan = svg_of("shihan", ["-n", NAME, "-d", DATE], tmp_path, out="b")
    assert column(shihan, bd.right_columns(False)[0], tol=2.0) == NAME + "殿"
    assert all(t[4] != bd.SZ_RANK for t in body(shihan))


@pytest.mark.parametrize("value", ['"belt"', '"Kyū grade"', "2", "1", '"yes"', '""'])
def test_ac11_bad_unit_is_an_error(value, home, tmp_path):
    text = with_award(_example(), "kyu", lambda b: set_key(b, UNIT_KEY, value))
    cfg = write_config(tmp_path, text)
    for extra in ([], ["--list"]):
        r = run(["-c", cfg, "-a", "dan", *extra, "--json"], home, tmp_path)
        assert r.returncode == 1, (value, extra)
        ev = support.events(r.stdout)
        assert [e["event"] for e in ev] == ["error"], ev
        msg = ev[0]["message"]
        for want in (cfg, UNIT_KEY, "kyu", '"dan"', '"kyu"'):
            assert want in msg, (want, msg)


@pytest.mark.parametrize("key", [CREST_KEY, MOTTO_KEY])
@pytest.mark.parametrize("value", ['"no"', "0", '"false"'])
def test_ac11_bad_sheet_key_is_an_error(key, value, home, tmp_path):
    text = with_award(_example(), "kyu", lambda b: set_key(b, key, value))
    cfg = write_config(tmp_path, text)
    r = run(["-c", cfg, "--list", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"], ev
    for want in (cfg, key, "kyu"):
        assert want in ev[0]["message"], (want, ev[0]["message"])


def test_ac11_sheet_keys_drive_the_sheet(tmp_path):
    """crest and motto are per award: a dan sheet without them, a kyū sheet
    with them (OQ-2)."""
    text = with_award(_example(), "dan", lambda b: set_key(set_key(b, CREST_KEY, "false"),
                                                           MOTTO_KEY, "false"))
    text = with_award(text, "kyu", lambda b: set_key(set_key(b, CREST_KEY, "true"),
                                                     MOTTO_KEY, "true"))
    cfg = write_config(tmp_path, text)
    got = svgs(["-a", "dan,kyu", "-n", NAME, "-r", "5", "-d", DATE], tmp_path, config=cfg)
    assert crest_parts(got["dan"]) == {"circles": 0, "mon": 0, "ring": 0}
    assert column(got["dan"], bd.X_MOTTO) == ""
    assert crest_parts(got["kyu"])["mon"] == 1 and crest_parts(got["kyu"])["ring"] > 0
    assert column(got["kyu"], bd.X_MOTTO) == MOTTO
    # only the motto: crest kept
    text = with_award(_example(), "dan", lambda b: set_key(b, MOTTO_KEY, "false"))
    dan = svg_of("dan", ["-d", DATE], tmp_path, config=write_config(tmp_path, text, "m.toml"),
                 out="m")
    assert crest_parts(dan)["mon"] == 1 and column(dan, bd.X_MOTTO) == ""
    # motto = false moves the columns (OQ-3 B), but the crest stays centred
    assert column(dan, bd.X_HEADING - SHIFT, tol=0.5) == "段位免状"
    assert f'translate({bd.CREST_C[0]:.3f} {bd.CREST_C[1]:.3f})' in dan


def test_ac11_dojo_overrides_heading_and_formula(tmp_path):
    text = with_award(_example(), "kyu",
                      lambda b: b.replace(KYU_HEADING, "級位免状").replace(KYU_FORMULA, "右授与ス"))
    cfg = write_config(tmp_path, text)
    cols = set(columns(svg_of("kyu", ["-d", DATE], tmp_path, config=cfg)).values())
    assert "級位免状" in cols and "右授与ス" in cols and KYU_HEADING not in cols


def test_ac11_save_round_trip(tmp_path):
    c = config_mod.load(EX)
    path = config_mod.save(c, str(tmp_path / "saved" / "dojo.toml"))
    back = config_mod.load(path)
    assert back.awards == c.awards
    args = ["-a", "all", "-n", NAME, "-r", "2", "-d", DATE]
    a, b = svgs(args, tmp_path, out="a"), svgs(args, tmp_path, config=path, out="b")
    assert a == b and set(a) == set(AWARDS)
    args = ["-a", "kyu", "-n", "", "-r", "white-yellow", "-d", ""]
    assert svgs(args, tmp_path, out="c") == svgs(args, tmp_path, config=path, out="d")


def test_ac11_save_writes_new_keys_only_where_needed(tmp_path):
    """Agreement 6: grade_column is "kyu" only for a kyū award, true/false
    otherwise; crest and motto are written only when false.  A config with
    no kyū award saves byte for byte as 0.4.0 did."""
    c = config_mod.load(EX)
    text = Path(config_mod.save(c, str(tmp_path / "a" / "dojo.toml"))).read_text(encoding="utf-8")
    kyu, dan = award_block(text, "kyu"), award_block(text, "dan")
    assert re.search(rf'^{UNIT_KEY} = "kyu"$', kyu, re.M), kyu
    assert re.search(rf"^{CREST_KEY} = false$", kyu, re.M), kyu
    assert re.search(rf"^{MOTTO_KEY} = false$", kyu, re.M), kyu
    assert re.search(rf"^{UNIT_KEY} = true$", dan, re.M), dan
    assert not re.search(rf"^(?:{CREST_KEY}|{MOTTO_KEY}) =", dan, re.M), dan
    # the 0.4.0 form of a dan award: slug, heading, formula, grade_column
    assert [l.split(" =")[0] for l in dan.strip().splitlines()[1:]] == \
        ["slug", "heading", "formula", UNIT_KEY]


def test_ac11_old_configuration_works(home, tmp_path):
    """A dojo.toml from before this item, grade_column true/false and no new
    keys, lists and draws as before (the goldens prove the bytes)."""
    cfg = str(support.DATA / "minimal.toml")
    r = run(["-c", cfg, "--list", "-a", "all"], home, tmp_path)
    assert r.returncode == 0, r.stderr


# ------------------------------------------------------------------ AC-12 ----
def _glyph_fail(args, cfg, home, tmp_path, out_name="out"):
    out = tmp_path / out_name
    r = run(["-c", cfg, *args, "-v", "overlay-flat", "-f", "pdf", f"--out={out}", "--json"],
            home, tmp_path)
    ev = support.events(r.stdout)
    return r, ev, out


def test_ac12_kyu_heading_checked_first(home, tmp_path):
    text = with_award(_example(), "kyu", lambda b: b.replace(KYU_HEADING, "級位𠮷定証"))
    cfg = write_config(tmp_path, text)
    r, ev, out = _glyph_fail(["-a", "kyu"], cfg, home, tmp_path)
    assert r.returncode == 1 and [e["event"] for e in ev] == ["error"], ev
    msg = ev[0]["message"]
    assert "𠮷" in msg and "U+20BB7" in msg and "the heading of [[awards]] 'kyu'" in msg, msg
    assert not out.exists()


def test_ac12_kyu_formula_and_rank_checked_first(home, tmp_path):
    text = with_award(_example(), "kyu", lambda b: b.replace(KYU_FORMULA, "右𠮷定ス"))
    cfg = write_config(tmp_path, text)
    r, ev, out = _glyph_fail(["-a", "kyu"], cfg, home, tmp_path)
    assert r.returncode == 1 and "the formula of [[awards]] 'kyu'" in ev[0]["message"]
    r, ev, out = _glyph_fail(["-a", "kyu", "--rank=𠮷級"], EX, home, tmp_path)
    assert r.returncode == 1 and "--rank" in ev[0]["message"] and "U+20BB7" in ev[0]["message"]
    assert not out.exists()


@pytest.mark.render
def test_ac12_what_a_kyu_sheet_does_not_draw_is_not_checked(home, tmp_path):
    """The crest ring and the motto are not on a kyū sheet, so a character
    their fonts lack does not stop a kyū-only run (and does stop a dan one)."""
    text = _example().replace('crest_ring = "〇〇道場"', 'crest_ring = "한한한한"') \
                     .replace('text = "柔能制剛"', 'text = "柔能𠮷剛"')
    assert "한한한한" in text and "柔能𠮷剛" in text
    cfg = write_config(tmp_path, text)
    r, ev, out = _glyph_fail(["-a", "kyu", "-d", DATE], cfg, home, tmp_path)
    assert r.returncode == 0, ev
    assert ev[-1]["files"] == [str(out / "kyu-overlay-flat-a3-sample.pdf")]
    r, ev, _ = _glyph_fail(["-a", "dan", "-d", DATE], cfg, home, tmp_path, "dan")
    assert r.returncode == 1 and [e["event"] for e in ev] == ["error"]
    assert "[dojo] crest_ring" in ev[0]["message"] or "[motto] text" in ev[0]["message"]


# ------------------------------------------------------------------ AC-13 ----
@pytest.mark.render
def test_ac13_json_events(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-d", DATE, f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["progress"] * 3 + ["file", "done"]
    progress = ev[:3]
    assert all(set(p) == {"event", "step", "total", "award", "variant", "stage", "label"}
               for p in progress)
    assert [(p["step"], p["total"], p["award"], p["variant"], p["stage"]) for p in progress] \
        == [(1, 3, "kyu", "overlay", "text"), (2, 3, "kyu", "overlay", "ink"),
            (3, 3, "kyu", "overlay", "pdf")]
    assert [p["label"] for p in progress] == [
        "kyu overlay: rendering the text", "kyu overlay: grading the ink",
        "kyu overlay: writing the PDF"]
    f = str(out / "kyu-overlay-a3-sample.pdf")
    assert ev[3] == {"event": "file", "path": f}
    assert ev[4] == {"event": "done", "out": str(out), "files": [f]}
    assert bd.STAGES == {"text": "rendering the text", "ink": "grading the ink",
                         "pdf": "writing the PDF", "png": "writing the PNG"}


@pytest.mark.render
def test_ac13_default_run_totals(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-d", DATE, f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    progress = [e for e in ev if e["event"] == "progress"]
    assert [(p["award"], p["stage"]) for p in progress] == [
        (a, s) for a in AWARDS for s in ("text", "ink", "pdf")]
    assert all(p["total"] == 3 * len(AWARDS) for p in progress)
    assert ev[-1]["files"] == [str(out / f"{a}-overlay-a3-sample.pdf") for a in AWARDS]


# ------------------------------------------------------------------ AC-14 ----
# no-honorific passes -r shodan to every award, which a kyū award refuses
# (AC-8); the other -a all cases on the example are these.
@pytest.mark.parametrize("case_id", ["sample", "blank", "filled"])
def test_ac14_example_as_it_is_still_draws_the_goldens(case_id, tmp_path):
    """The goldens run on the example without kyu (golden_lib); here the
    same cases run on the example as it is, and its dan, shihan and renshi
    files must still be the goldens' bytes."""
    case = next(c for c in CASES if c["id"] == case_id)
    golden = golden_lib.load_manifest()["cases"][case_id]
    out = tmp_path / "out"
    bd.main(["-c", EX, *case["argv"], f"--out={out}"])
    files = {golden_lib.sized(n): sha for n, sha in golden["files"].items()}
    written = sorted(p.name for p in out.iterdir() if p.is_file())
    assert sorted(n for n in written if not n.startswith("kyu-")) == sorted(files)
    assert [n for n in written if n.startswith("kyu-")], written
    for name, sha in files.items():
        want = golden_lib.sized(golden_lib.blob(sha))
        assert (out / name).read_text(encoding="utf-8") == want, name


def test_ac14_baseline_copy_is_the_example_without_kyu():
    text = _example()
    stripped = golden_lib.baseline_awards_only(text)
    assert 'slug = "kyu"' in text and 'slug = "kyu"' not in stripped
    for slug in ("dan", "shihan", "renshi"):
        assert award_block(stripped, slug) == award_block(text, slug)
    assert stripped.split("[[awards]]", 1)[0] == text.split("[[awards]]", 1)[0]
    assert stripped.split("\n[sample]\n", 1)[1] == text.split("\n[sample]\n", 1)[1]


# ------------------------------------------------------------------ AC-15 ----
@pytest.mark.slow
@pytest.mark.render
def test_ac15_installed_wheel(installed, home, tmp_path):
    exe = [str(installed["menkyo"])]
    site = next(installed["venv"].glob("lib/python*/site-packages"))
    ex = str(site / "menkyo" / "example.toml")      # the installed copy's own
    r = run(["--example-config"], home, tmp_path, exe=exe)
    assert r.returncode == 0 and 'slug = "kyu"' in r.stdout
    r = run(["--list"], home, tmp_path, exe=exe)
    assert r.stdout.splitlines() == [f"{a}-overlay-a3-sample.pdf" for a in AWARDS]
    r = run([f"--config={ex}", "--awards=kyu", "--variants=overlay-flat", "--formats=pdf,svg", "--name=",
             "--rank=white-yellow", f"--date={DATE}", "--json"], home, tmp_path, exe=exe)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
    docs = home / "Documents" / "Menkyo"
    stem = docs / "kyu-overlay-flat-a3-white-yellow"
    ev = support.events(r.stdout)
    assert ev[-1] == {"event": "done", "out": str(docs),
                      "files": [f"{stem}.pdf", f"{stem}.svg"]}
    assert printed_rank(Path(f"{stem}.svg").read_text(encoding="utf-8")) == "準五級"
    r = run(["-c", ex, "-a", "kyu", "--rank=purple", "--json"], home, tmp_path, exe=exe)
    assert r.returncode == 1 and support.events(r.stdout)[0]["event"] == "error"
    r = run(["-c", ex, "-a", "kyu", "--paper", "a4", "-v", "overlay", "-d", DATE, "--json"],
            home, tmp_path, exe=exe)
    assert r.returncode == 0, r.stderr
    assert page_size_pt(docs / "kyu-overlay-a4-sample.pdf") == pytest.approx(A4_PT, abs=0.01)


# ------------------------------------------------------------------ AC-16 ----
def _readme():
    return (support.REPO / "README.md").read_text(encoding="utf-8")


def _decisions():
    return (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")


def test_ac16_readme():
    text = _readme()
    # the options table: --rank says what a kyū award takes
    row = next(l for l in text.splitlines() if l.startswith("| `-r`, `--rank"))
    assert "級" in row, row
    # the forms, the belts and 準 are explained
    for want in ("white-yellow", "yellow-orange", "orange-green", "準五級", "jun5",
                 "gokyu", KYU_HEADING, KYU_FORMULA):
        assert want in text, want
    for colour in ("white", "yellow", "orange", "green", "blue", "brown"):
        assert colour in text, colour
    # the configuration example shows the kyū award and its keys
    assert re.search(r'^slug = "kyu"', text, re.M)
    assert re.search(rf'^{UNIT_KEY} = "kyu"', text, re.M)
    assert re.search(rf"^{CREST_KEY} = false", text, re.M)
    assert re.search(rf"^{MOTTO_KEY} = false", text, re.M)
    # the glyph-check paragraph no longer says the art is always on the ring
    para = text.split("A character the fonts do not have", 1)[1].split("\n\n", 1)[0]
    assert re.search(r"ky[uū]|without a crest|no crest|crest = false", para), para
    assert re.search(r"ky[uū]", text.split("## Quick start", 1)[0], re.I), \
        "the introduction does not mention kyū certificates"


def test_ac16_example_comments():
    """[sample] rank's comment says what the sample is on a kyū sheet."""
    sample = _example().split("\n[sample]\n", 1)[1]
    rank_comment = sample.split("rank =", 1)[0].rsplit("\n\n", 1)[-1]
    assert "五級" in rank_comment, rank_comment


def test_ac16_decisions_entry():
    text = _decisions()
    body, open_ = text.split("\n## Open\n", 1)
    entries = house_style.decisions_entries(text)
    last = entries[-1]
    heading = last.splitlines()[0]
    assert re.match(r"^## \d{4}-\d{2}-\d{2} – ", heading), heading
    assert re.search(r"ky[uū]", heading, re.I), heading
    for want in (KYU_HEADING, KYU_FORMULA, "準", "white-yellow", UNIT_KEY, "0.5.0"):
        assert want in last, want
    # what it overrides, by title: the precept on every document, and every
    # unrecognised --rank passing through
    flat = " ".join(last.split())
    for title in ("Purple menkyo, and a precept column", "Printing the three hand slots"):
        assert title in flat, title
    # the earlier entries are history: pinned, unchanged (house-style-sweep AC-11)
    pins = house_style.pinned_hashes()
    blocks = house_style.decisions_blocks(text)
    assert [house_style.entry_hash(b) for b in blocks[:len(pins)]] == pins
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    assert not [i for i in items if re.search(r"ky[uū]", i, re.I)], items
    assert [i for i in items if i.startswith("An annotated version in Dutch")], items


# OQ-8, recommended: an explainer for the recipient, like the other three.
def test_ac16_recipient_explainer():
    p = support.REPO / "docs" / "kyu-explained.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    for want in (KYU_HEADING, KYU_FORMULA, "準", "If you are adapting this document"):
        assert want in text, want
    assert "柔能制剛" not in text           # the precept is configuration


# ------------------------------------------------------------------ AC-17 ----
# OQ-9, recommended: a new award and new --rank behaviour make 0.5.0.
def test_ac17_version(home, tmp_path):
    assert support.project_version() == "0.5.0"
    r = run(["--version"], home, tmp_path)
    assert (r.returncode, r.stdout) == (0, "menkyo 0.5.0\n")
