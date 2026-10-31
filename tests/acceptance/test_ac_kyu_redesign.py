"""kyu-redesign: the kyū certificate rebuilt as a horizontal A4 portrait sheet
(yokogaki), printed in Noto Serif JP SemiBold without the sumi ink, with the
dōjō's crest as a light watermark behind the body text.

Contract: docs/work/kyu-redesign/acceptance.md.  The approved mock-up
(2026-10-30) is the reference for positions and sizes (MOCK below).  Where
the contract follows a recommendation still open (OQ-n), the test says so,
and the constants below are where a different answer is changed.

User approval (2026-10-30): the horizontal portrait sheet is the only kyū
sheet.  An award counting in kyū (grade_column = "kyu") always gets it, a dan
award or a licence is always vertical; there is no layout key, and the
per-award `motto` key and its 10 mm shift are gone.

Every run passes -c with the shipped example, the 0.5.0 example kept in
kyu_redesign/ (its dan, shihan and renshi only), or a configuration written
here; HOME and XDG_CONFIG_HOME are isolated (conftest, support).
"""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import namedtuple
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod
from menkyo import render as renderer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import house_style  # noqa: E402

EX = str(support.EXAMPLE)
# The example as 0.5.0 shipped it (ec62ba5).  Its kyū block sets
# `motto = false`, an error now, so it is used without that block.
EX_050 = str(HERE / "kyu_redesign" / "example-0.5.0.toml")
# Computed at ec62ba5 (see acceptance.md, Test changes).
PINS = json.loads((HERE / "kyu_redesign" / "pins-0.5.0.json").read_text(encoding="utf-8"))

DATE = "2026-09-05"
DATE_KANJI = "西暦二〇二六年九月五日"
NAME = "ヤン・ヤンセン"
ART, DOJO, TITLE, SIGNER, MOTTO = "〇〇流柔術", "〇〇道場", "師範", "山田太郎", "柔能制剛"
CREST_RING = "〇〇道場"
HEADING = "級位認定証"
PLAIN = ["overlay", "overlay-flat", "proof"]

# User approval, OQ-3: no layout key.  A key of that name is an unknown key,
# ignored like any other; `motto` was a key and is now an error.
LAYOUT_KEY, MOTTO_KEY = "layout", "motto"
# OQ-6: the body text, per award, one string per printed line.
BODY_KEY = "body"
BODY = ["上記の者は本会所定の審査に合格したので", "ここに認定します"]
# OQ-5: the watermark's grey, per award, as a fraction of black.
WATERMARK_KEY, WATERMARK = "watermark", 0.08

# The horizontal layout's own units: A4 portrait, mm.
W, H = 210.0, 297.0
S2 = math.sqrt(2)
# [paper] border and safe_inset are A3 millimetres; on A4 they scale by 1/√2.
BORDER, SAFE = 22.0 / S2, 38.0 / S2
A4P_PT = (210 * 72 / 25.4, 297 * 72 / 25.4)
A3P_PT = (297 * 72 / 25.4, 420 * 72 / 25.4)

# The approved mock (kyu-a4-crest-C.png): each line's centre y and size, mm.
MOCK = {
    "title": (58.0, 16.0), "name": (104.0, 11.0), "grade": (140.0, 22.0),
    "body1": (180.0, 7.4), "body2": (193.0, 7.4), "date": (213.0, 6.6),
    "art": (236.0, 8.2), "dojo": (249.0, 8.2), "sig": (264.0, 8.2),
}
MOCK_CREST = (105.0, 168.0, 60.0)       # centre x, y and outer ring radius
Y_TOL = 4.0                             # mm, a line's centre against the mock
SIZE_TOL = 0.15                         # relative, a line's size against the mock
FILLED_LINES = [HEADING, NAME + "殿", "準五級", BODY[0], BODY[1], DATE_KANJI,
                ART, DOJO, TITLE + SIGNER]
FILLED = ["-n", NAME, "-r", "white-yellow", "-d", DATE]
BLANK = ["-n", "", "-r", "", "-d", ""]


# ----------------------------------------------------------------- helpers ----
def _example():
    return support.EXAMPLE.read_text(encoding="utf-8")


def _blocks(text):
    lines = text.splitlines(keepends=True)
    heads = [i for i, l in enumerate(lines) if re.match(r"^\s*\[", l)] + [len(lines)]
    return lines, list(zip(heads, heads[1:]))


def award_block(text, slug):
    """The [[awards]] block of `slug`, header to next table header."""
    lines, spans = _blocks(text)
    for start, end in spans:
        block = "".join(lines[start:end])
        if lines[start].strip() == "[[awards]]" and re.search(
                rf'^\s*slug\s*=\s*"{re.escape(slug)}"', block, re.M):
            return block
    raise AssertionError(f"no [[awards]] block for {slug!r}")


def with_award(text, slug, edit):
    block = award_block(text, slug)
    return text.replace(block, edit(block), 1)


def drop_key(block, key):
    """`block` without `key`, a one-line or a multi-line array value."""
    return re.sub(rf"^\s*{key}\s*=\s*(?:\[[^\]]*\]|[^\n]*)\n", "", block, flags=re.M)


def set_key(block, key, value):
    """`block` with `key = value` (a TOML literal), replacing the key if the
    block has it, else added after the slug."""
    block = drop_key(block, key) if re.search(rf"^\s*{key}\s*=", block, re.M) else block
    return re.sub(r'^(\s*slug\s*=.*)$', lambda m: f"{m.group(1)}\n{key} = {value}",
                  block, count=1, flags=re.M)


def toml_list(items):
    return "[" + ", ".join(json.dumps(s, ensure_ascii=False) for s in items) + "]"


def write_config(tmp_path, text, name="kyu.toml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def config_with(tmp_path, edit, base=None, name="kyu.toml", slug="kyu"):
    """The example (or `base`) with `slug`'s block passed through edit()."""
    return write_config(tmp_path, with_award(base or _example(), slug, edit), name)


def landscape_050(tmp_path):
    """The 0.5.0 example without its kyū block: dan, shihan and renshi as
    0.5.0 shipped them."""
    sys.path.insert(0, str(support.TESTS / "regression"))
    import golden_lib
    text = golden_lib.baseline_awards_only(Path(EX_050).read_text(encoding="utf-8"))
    assert 'slug = "kyu"' not in text
    return write_config(tmp_path, text, "landscape-0.5.0.toml")


def run(args, home, tmp_path, exe=None, **env):
    return support.run_menkyo([str(a) for a in args], support.isolated_env(home, **env),
                              tmp_path, exe=exe)


def listing(args, home, tmp_path, config=EX):
    r = run(["-c", config, "--list", *args, f"--out={tmp_path / 'o'}"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "o").exists()
    return r.stdout.splitlines()


_n = [0]


def svgs(args, tmp_path, config=EX, variant="overlay-flat", no_ink=False):
    """main() in-process, -f svg; {award: svg text}.  No --no-ink by default:
    a horizontal sheet is never inked, and its SVG must show that."""
    _n[0] += 1
    o = tmp_path / f"svg{_n[0]}"
    bd.main(["-c", config, "-v", variant, "-f", "svg", "--suffix", "t",
             *(["--no-ink"] if no_ink else []), *args, f"--out={o}"])
    return {p.name.split(f"-{variant}-")[0]: p.read_text(encoding="utf-8")
            for p in sorted(o.glob(f"*-{variant}-*-t.svg"))}


def kyu_svg(args, tmp_path, config=EX, variant="overlay-flat", slug="kyu"):
    return svgs(["-a", slug, *args], tmp_path, config=config, variant=variant)[slug]


@pytest.fixture(scope="module")
def filled(tmp_path_factory):
    """The example's kyū sheet with FILLED, A4, overlay-flat: drawn once for
    every test that reads it (review round 3, R-7)."""
    return kyu_svg(FILLED, tmp_path_factory.mktemp("filled"))


def fails(args, config=EX, tmp_path=None):
    """main()'s SystemExit message for a run that must fail, nothing written."""
    out = ["--out", str(tmp_path / "fail")] if tmp_path else []
    with pytest.raises(SystemExit) as e:
        bd.main(["-c", config, "-v", "overlay-flat", "-f", "svg", *args, *out])
    assert isinstance(e.value.code, str), e.value.code
    if tmp_path:
        assert not (tmp_path / "fail").exists() or not any((tmp_path / "fail").iterdir())
    return e.value.code


# ---- reading a horizontal sheet's SVG ----------------------------------------
# Printed text is every <text> in the ink colour, at its own x and y in the
# layout's millimetres (inside the A3 sheet's scale wrapper, if any); the
# watermark's ring lettering is in the watermark's grey and is left out.
Txt = namedtuple("Txt", "x y size family anchor s transform")
_ANCHOR = {"start": 0.0, "middle": 0.5, "end": 1.0}
SVG_NS = "{http://www.w3.org/2000/svg}"


def printed(svg):
    out = []
    for el in ET.fromstring(svg).iter(SVG_NS + "text"):
        if el.get("fill") != bd.INK:
            continue
        out.append(Txt(float(el.get("x")), float(el.get("y")), float(el.get("font-size")),
                       el.get("font-family"), el.get("text-anchor", "start"),
                       el.text or "", el.get("transform")))
    return out


def advance(s, size, family):
    f = renderer.face(family)
    return sum(f.glyph(c)[1] for c in s) / f.upem * size


def extent(t):
    w = advance(t.s, t.size, t.family)
    left = t.x - _ANCHOR[t.anchor] * w
    return left, left + w


def centre_y(t):
    return t.y - bd.BASELINE_DROP * t.size


Line = namedtuple("Line", "text y left right size parts")


def lines(svg):
    """The printed text as lines, top to bottom: elements whose centres lie
    within 3 mm of each other, read left to right, whitespace (U+3000
    included) dropped.  `size` is the line's largest, `y` its centre."""
    ts = sorted(printed(svg), key=centre_y)
    groups = []
    for t in ts:
        if groups and centre_y(t) - centre_y(groups[-1][0]) <= 3.0:
            groups[-1].append(t)
        else:
            groups.append([t])
    out = []
    for g in groups:
        g = sorted(g, key=lambda t: extent(t)[0])
        big = max(g, key=lambda t: t.size)
        out.append(Line(re.sub(r"\s", "", "".join(t.s for t in g)), centre_y(big),
                        min(extent(t)[0] for t in g), max(extent(t)[1] for t in g),
                        big.size, g))
    return out


def texts_of(svg):
    return [l.text for l in lines(svg)]


def by_text(svg):
    return {l.text: l for l in lines(svg)}


def grey(w):
    v = round(255 * (1 - w))
    return f"#{v:02x}{v:02x}{v:02x}"


_CREST_G = re.compile(r'<g transform="translate\(([-\d.]+) ([-\d.]+)\)">\s*'
                      r'<circle r="([\d.]+)" fill="none" stroke="(#[0-9a-fA-F]{6})"')


def watermark(svg):
    """(cx, cy, r, grey, position in the SVG) of the crest, or None."""
    m = _CREST_G.search(svg)
    return (float(m[1]), float(m[2]), float(m[3]), m[4].lower(), m.start()) if m else None


_GUIDE = re.compile(r'<(?:rect|circle) [^>]*stroke="#(?:d8c9a8|cddbe8|e4b9b9)"[^>]*/>')


def guides(svg):
    """The proof's guides as (tag, {attr: value}), numbers as floats."""
    out = []
    for g in _GUIDE.findall(svg):
        attrs = dict(re.findall(r'(\S+)="([^"]*)"', g))
        for k, v in attrs.items():
            try:
                attrs[k] = float(v)
            except ValueError:
                pass
        out.append((g[1:g.index(" ")], attrs))
    return out


def unwrap_a3(svg):
    """An A3 kyū SVG's content with the sheet and its scale wrapper taken
    off, to compare with the A4 one's."""
    assert '<g transform="scale(1.4142135624)">' in svg, svg[:300]
    return printed(svg)


def page_mm(svg):
    root = ET.fromstring(svg)
    return (float(root.get("width").removesuffix("mm")),
            float(root.get("height").removesuffix("mm")))


# ---- PDFs and PNGs -----------------------------------------------------------
def page_size_pt(pdf):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return tuple(doc[0].get_size())
    finally:
        doc.close()


def alpha(png):
    from PIL import Image
    import numpy as np
    with Image.open(png) as im:
        mode = im.mode
        a = np.asarray(im.getchannel("A"))
    return mode, a


def _tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()} if root.exists() else {}


# ------------------------------------------------------------------- AC-1 ----
def test_ac1_example_kyu_award():
    c = config_mod.load(EX)
    assert c.slugs == ["dan", "shihan", "renshi", "kyu"]
    kyu = c.award("kyu")
    assert kyu.heading == HEADING and kyu.unit == "kyu" and kyu.grade_column
    assert list(getattr(kyu, BODY_KEY)) == BODY                         # OQ-6
    assert getattr(kyu, WATERMARK_KEY) == pytest.approx(WATERMARK)      # OQ-5
    assert kyu.crest is True                                            # OQ-4
    block = award_block(_example(), "kyu")
    assert re.search(rf"^\s*{WATERMARK_KEY}\s*=\s*0\.08\b", block, re.M), block
    assert re.search(rf"^\s*{BODY_KEY}\s*=", block, re.M), block
    assert not re.search(rf"^\s*(?:crest|{MOTTO_KEY}|{LAYOUT_KEY}|formula)\s*=", block,
                         re.M), block
    # the other three as they were
    for slug in ("dan", "shihan", "renshi"):
        assert award_block(_example(), slug) == award_block(
            Path(EX_050).read_text(encoding="utf-8"), slug)


def test_ac1_only_the_kyu_block_changed():
    """The example's settings differ from 0.5.0's in the kyū block alone
    (comments, the key legend among them, may change)."""
    def settings(text):
        rest = text.replace(award_block(text, "kyu"), "")
        return [l.split("#")[0].rstrip() for l in rest.splitlines()
                if l.strip() and not l.lstrip().startswith("#")]
    assert settings(_example()) == settings(Path(EX_050).read_text(encoding="utf-8"))


def test_ac1_example_config_prints_it(home, tmp_path):
    # (kyu-grades' own copy of this check went, review round 3, R-4)
    r = run(["--example-config"], home, tmp_path)
    assert r.returncode == 0
    assert r.stdout.encode("utf-8") == support.EXAMPLE.read_bytes()


def test_ac1_example_comments():
    text = _example()
    legend = text.split("[[awards]]", 1)[0].rsplit("# ----", 2)[-2]
    for key in (BODY_KEY, WATERMARK_KEY):
        assert re.search(rf"#\s+{key}\b", legend), (key, legend)
    assert not re.search(rf"#\s+(?:{MOTTO_KEY}|{LAYOUT_KEY})\s", legend), legend
    block = award_block(text, "kyu")
    comments = " ".join(l for l in block.splitlines() if l.lstrip().startswith("#"))
    assert re.search(r"horizontal|yokogaki|横書き", comments, re.I), comments
    assert re.search(r"A4", comments) and re.search(r"portrait", comments, re.I), comments
    assert re.search(r"watermark", comments, re.I), comments


# ------------------------------------------------------------------- AC-2 ----
# OQ-1: a horizontal sheet is A4 portrait; [paper] size is the landscape
# sheets' default and does not apply to it; --paper applies to every award.
def test_ac2_default_listing(home, tmp_path):
    assert listing([], home, tmp_path) == [
        "dan-overlay-a3-sample.pdf", "shihan-overlay-a3-sample.pdf",
        "renshi-overlay-a3-sample.pdf", "kyu-overlay-a4-sample.pdf"]
    assert listing(["--all"], home, tmp_path) == [
        f"{a}-{v}-{'a4' if a == 'kyu' else 'a3'}-sample.pdf"
        for a in ("dan", "shihan", "renshi", "kyu") for v in PLAIN]


NAME_CASES = [
    (["-a", "kyu"], ["kyu-overlay-a4-sample.pdf"]),
    (["-a", "kyu", "--paper", "a4"], ["kyu-overlay-a4-sample.pdf"]),
    (["-a", "kyu", "--paper", "a3"], ["kyu-overlay-a3-sample.pdf"]),
    (["-a", "kyu", "--paper", "A3"], ["kyu-overlay-a3-sample.pdf"]),
    (["-a", "kyu", "-v", "all", "-f", "pdf,png"],
     [f"kyu-{v}-a4-sample.{e}" for v in PLAIN for e in ("pdf", "png")]),
    (["-a", "kyu", "-r", "yellow", "-n", NAME], ["kyu-overlay-a4-yellow-ヤン-ヤンセン.pdf"]),
    (["-a", "kyu", "--suffix", ""], ["kyu-overlay-a4.pdf"]),
    (["-a", "dan,kyu", "-r", "3"], ["dan-overlay-a3-3.pdf", "kyu-overlay-a4-3.pdf"]),
    (["-a", "dan,kyu", "--paper", "a4"], ["dan-overlay-a4-sample.pdf",
                                          "kyu-overlay-a4-sample.pdf"]),
    (["-a", "dan,kyu", "--paper", "a3"], ["dan-overlay-a3-sample.pdf",
                                          "kyu-overlay-a3-sample.pdf"]),
]


@pytest.mark.parametrize("args, names", NAME_CASES, ids=[" ".join(c[0]) for c in NAME_CASES])
def test_ac2_names(args, names, home, tmp_path):
    assert listing(args, home, tmp_path) == names


def test_ac2_paper_size_key_does_not_move_kyu(home, tmp_path):
    for size in ("a3", "a4"):
        cfg = write_config(tmp_path, _example().replace('size = "a3"', f'size = "{size}"'),
                           f"{size}.toml")
        assert listing(["-a", "dan,kyu"], home, tmp_path, config=cfg) == [
            f"dan-overlay-{size}-sample.pdf", "kyu-overlay-a4-sample.pdf"]


def test_ac2_planned_events(home, tmp_path):
    r = run(["-c", EX, "--list", "--json", "-a", "kyu", "-v", "all"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert support.events(r.stdout) == [
        {"event": "planned", "file": f"kyu-{v}-a4-sample.pdf"} for v in PLAIN]


def test_ac2_a3_is_the_a4_layout_scaled(filled, tmp_path):
    """A4 portrait by default (the example's [paper] size is a3), no
    wrapper; --paper a3 the same layout inside the √2 wrapper.  (An explicit
    --paper a4: the AC-8 render's page size.)"""
    a4, a3 = filled, kyu_svg(FILLED + ["--paper", "a3"], tmp_path)
    assert page_mm(a4) == pytest.approx((210.0, 297.0), abs=0.001)
    assert page_mm(a3) == pytest.approx((297.0, 420.0), abs=0.001)
    assert '<g transform="scale(1.4142135624)">' not in a4
    assert "scale(0.7071067812)" not in a4 + a3
    assert unwrap_a3(a3) == printed(a4)
    assert watermark(a3)[:4] == watermark(a4)[:4]


def test_ac2_help_says_portrait(home, tmp_path):
    r = run(["-c", EX, "--help"], home, tmp_path, COLUMNS="1000")
    assert r.returncode == 0, r.stderr
    # The option's own help line (COLUMNS=1000 keeps it on one line), not the
    # usage line, which names `--paper SIZE` first (review R-1).
    paper = re.split(r"\n  --paper SIZE", r.stdout, maxsplit=1)[1].split("\n  -", 1)[0]
    assert re.search(r"portrait", paper, re.I), paper
    assert re.search(r"ky[uū]|horizontal", paper, re.I), paper


# ------------------------------------------------------------------- AC-3 ----
def test_ac3_lines_top_to_bottom(filled):
    # the example has a precept, and the kyū sheet does not print it (AC-5)
    assert config_mod.load(EX).motto == MOTTO
    assert texts_of(filled) == FILLED_LINES


def test_ac3_sample_sheet(tmp_path):
    """No fill-in flags: the example's [sample] stand-ins, 5 as 五級."""
    got = texts_of(kyu_svg(["-d", DATE], tmp_path))
    assert got == [HEADING, "ジョン・ドウ殿", "五級", *BODY, DATE_KANJI, ART, DOJO,
                   TITLE + SIGNER], got


def test_ac3_mincho_ink_no_vertical_tricks(tmp_path):
    svg = kyu_svg(["-n", "ヘールト・ヤンセン", "-r", "jun3", "-d", DATE], tmp_path)
    ts = printed(svg)
    assert ts and {t.family for t in ts} == {bd.FONT_CREST}             # Noto Serif JP
    assert bd.FONT_BODY not in svg                                      # no Yuji Boku
    assert all(t.transform is None for t in ts), [t for t in ts if t.transform]
    assert "<image" not in svg                                          # no ink raster
    # ー is not turned and small kana are not shifted: a horizontal line
    name = by_text(svg)["ヘールト・ヤンセン殿"]
    assert len({round(centre_y(t), 2) for t in name.parts if t.s.strip() != "殿"}) == 1


def test_ac3_blank_slots(tmp_path):
    svg = kyu_svg(BLANK, tmp_path)
    assert texts_of(svg) == [HEADING, *BODY, "西暦年月日", ART, DOJO, TITLE + SIGNER]
    assert "殿" not in "".join(t.s for t in printed(svg))      # OQ-7: no name, no 殿
    # the blank date leaves room: 4 year, 2 month, 3 day characters
    date = by_text(svg)["西暦年月日"]
    glyphs = []
    for t in date.parts:
        left, _ = extent(t)
        for ch in t.s:
            w = advance(ch, t.size, t.family)
            if not ch.isspace():
                glyphs.append((ch, left, left + w))
            left += w
    glyphs.sort(key=lambda g: g[1])
    assert [g[0] for g in glyphs] == list("西暦年月日")
    size = date.size
    gaps = {g[0]: n[1] - g[2] for g, n in zip(glyphs, glyphs[1:])}
    assert gaps["暦"] >= 3.9 * size, gaps          # four year digits
    assert gaps["年"] >= 1.9 * size, gaps          # two for the month
    assert gaps["月"] >= 2.9 * size, gaps          # three for the day


# ------------------------------------------------------------------- AC-4 ----
def _named_lines(svg):
    ls = lines(svg)
    assert len(ls) == len(MOCK), [l.text for l in ls]
    return dict(zip(MOCK, ls))


@pytest.mark.parametrize("paper", [None, "a3"])
def test_ac4_positions_and_sizes_as_mocked(paper, filled, tmp_path):
    """Positions, sizes, centring, alignment and letter spacing, at A4 and
    A3 alike (review round 3, R-7: one test over the same sheet)."""
    got = _named_lines(kyu_svg(FILLED + ["--paper", paper], tmp_path) if paper else filled)
    for key, (y, size) in MOCK.items():
        line = got[key]
        assert line.y == pytest.approx(y, abs=Y_TOL), (key, line.y)
        assert line.size == pytest.approx(size, rel=SIZE_TOL), (key, line.size)
    # the grade is the most prominent, then the heading, then the name
    assert got["grade"].size > got["title"].size > got["name"].size > got["body1"].size
    # heading and grade letter-spaced
    title, grade = got["title"], got["grade"]
    assert title.right - title.left >= 1.25 * len(HEADING) * title.size
    assert grade.right - grade.left >= 1.10 * len("準五級") * grade.size
    # heading, name and grade centred
    for key in ("title", "name", "grade"):
        mid = (got[key].left + got[key].right) / 2
        assert mid == pytest.approx(W / 2, abs=1.0), (key, mid)
    # the body's lines start at one left edge; the date no further left
    assert got["body1"].left == pytest.approx(got["body2"].left, abs=0.5)
    assert got["date"].left >= got["body1"].left - 0.5
    # the issuer's three lines start at one left edge, right of centre
    lefts = [got[k].left for k in ("art", "dojo", "sig")]
    assert max(lefts) - min(lefts) <= 0.5, lefts
    block = (min(lefts) + max(got[k].right for k in ("art", "dojo", "sig"))) / 2
    assert block >= W / 2 + 5, block
    # the signatory's office and name on one line, a space apart
    sig = got["sig"]
    assert sig.text == TITLE + SIGNER
    solid = advance(TITLE + SIGNER, sig.size, bd.FONT_CREST)
    assert sig.right - sig.left >= solid + 0.5 * sig.size, (sig.right - sig.left, solid)


def test_ac4_inside_the_safe_area(filled, tmp_path):
    for args, svg in ((FILLED, filled), (BLANK, None),
                      (["-n", NAME, "-r", "10", "-d", "2026-12-31"], None)):
        for l in lines(svg or kyu_svg(args, tmp_path)):
            assert l.left >= SAFE - 0.01 and l.right <= W - SAFE + 0.01, (args, l.text)
            assert l.y - l.size / 2 >= SAFE and l.y + l.size / 2 <= H - SAFE, (args, l.text)


@pytest.mark.parametrize("value, grade", [("white-yellow", "準五級"), ("10", "十級"),
                                          ("三級", "三級")])
def test_ac4_a_long_grade_is_not_shrunk(value, grade, tmp_path):
    """Horizontally there is room: 準五級 is set at the size of 五級."""
    two = by_text(kyu_svg(["-n", "", "-r", "5", "-d", DATE], tmp_path))["五級"]
    got = by_text(kyu_svg(["-n", "", "-r", value, "-d", DATE], tmp_path))[grade]
    assert got.size == pytest.approx(two.size, abs=0.001)
    assert got.y == pytest.approx(two.y, abs=0.001)
    assert (got.left + got.right) / 2 == pytest.approx(W / 2, abs=1.0)


def test_ac4_a_long_name_shrinks_to_fit(filled, tmp_path):
    long = "アレクサンドリア・ファン・デル・ヴェステンハーゲン"
    short = by_text(filled)[NAME + "殿"]
    got = by_text(kyu_svg(["-n", long, "-r", "5", "-d", DATE], tmp_path))[long + "殿"]
    assert got.left >= SAFE - 0.01 and got.right <= W - SAFE + 0.01, (got.left, got.right)
    assert (got.left + got.right) / 2 == pytest.approx(W / 2, abs=1.0)
    assert got.size < short.size
    assert got.y == pytest.approx(short.y, abs=1.0)


def test_ac4_a_long_body_line_shrinks_to_fit(tmp_path):
    long = BODY[0] + BODY[1] + BODY[0]
    cfg = config_with(tmp_path, lambda b: set_key(b, BODY_KEY, toml_list([long, BODY[1]])))
    got = by_text(kyu_svg(FILLED, tmp_path, config=cfg))
    assert got[long].left >= SAFE - 0.01 and got[long].right <= W - SAFE + 0.01
    assert got[BODY[1]].left == pytest.approx(got[long].left, abs=0.5)


# Agreement 1: a long issuer line moves the block left (and shrinks it only
# if it would pass the centre), keeping room for the seal on every variant.
LONG_SIGNER = "ジョン・スミス・ドウ"          # a placeholder, nobody's name


def test_ac4_a_long_issuer_line_stays_inside(tmp_path):
    text = _example().replace('name = "山田太郎"', f'name = "{LONG_SIGNER}"')
    assert LONG_SIGNER in text
    cfg = write_config(tmp_path, text)
    flat = kyu_svg(FILLED, tmp_path, config=cfg)
    proof = kyu_svg(FILLED, tmp_path, config=cfg, variant="proof")
    assert printed(proof) == printed(flat)                  # the seal's room on both
    got = _named_lines(flat)
    assert got["sig"].text == TITLE + LONG_SIGNER
    lefts = [got[k].left for k in ("art", "dojo", "sig")]
    assert max(lefts) - min(lefts) <= 0.5, lefts
    for k in ("art", "dojo", "sig"):
        assert got[k].left >= SAFE - 0.01 and got[k].right <= W - SAFE + 0.01, (k, got[k])
    seal = [a for t, a in guides(proof) if t == "circle"]
    assert len(seal) == 1
    s = seal[0]
    assert s["cx"] - s["r"] > got["sig"].right + 1.0, (s, got["sig"].right)
    assert s["cx"] + s["r"] <= W - SAFE + 0.01, s
    assert s["cy"] + s["r"] <= H - SAFE + 0.01, s


def test_ac4_a_long_heading_stays_inside(tmp_path):
    """Agreement 1: seven or more characters tighten the spacing first."""
    heading = "級位認定証明書類"
    cfg = config_with(tmp_path, lambda b: b.replace(HEADING, heading))
    got = by_text(kyu_svg(FILLED, tmp_path, config=cfg))[heading]
    assert got.left >= SAFE - 0.01 and got.right <= W - SAFE + 0.01, got
    assert (got.left + got.right) / 2 == pytest.approx(W / 2, abs=1.0)


def test_ac4_text_drop_does_not_move_it(filled, tmp_path):
    cfg = write_config(tmp_path, _example().replace("text_drop = 0.05", "text_drop = 0"))
    assert "text_drop = 0\n" in Path(cfg).read_text(encoding="utf-8")
    assert printed(kyu_svg(FILLED, tmp_path, config=cfg)) == printed(filled)


# ------------------------------------------------------------------- AC-5 ----
# (the precept never printed on the kyū sheet: test_ac3_lines_top_to_bottom)
def test_ac5_watermark_behind_the_body(filled):
    svg = filled
    wm = watermark(svg)
    assert wm, "no crest on the kyū sheet"
    cx, cy, r, colour, at = wm
    assert cx == pytest.approx(W / 2, abs=0.001)
    assert cy == pytest.approx(MOCK_CREST[1], abs=10.0)
    assert r == pytest.approx(MOCK_CREST[2], abs=5.0)                   # ~120 mm across
    assert colour == grey(WATERMARK) == "#ebebeb"
    # drawn first: the text prints over it
    first_text = svg.index(f'fill="{bd.INK}"')
    assert at < first_text
    # all of it in the grey, the ring lettering included; none in ink
    assert svg.count(f'fill="{colour}" fill-rule="evenodd"') == 1        # the mon
    assert len(re.findall(rf'<circle r="[\d.]+" fill="none" stroke="{colour}"', svg)) == 2
    ring = [el.text for el in ET.fromstring(svg).iter(SVG_NS + "text")
            if el.get("fill") == colour]
    assert sorted(ring) == sorted(ART + CREST_RING), ring
    assert 'fill-rule="evenodd"' not in svg.replace(f'fill="{colour}" fill-rule="evenodd"', "")


@pytest.mark.parametrize("value, want", [("0.2", "#cccccc"), ("0.05", "#f2f2f2"),
                                         ("1", "#000000")])
def test_ac5_watermark_grey_is_configurable(value, want, tmp_path):
    cfg = config_with(tmp_path, lambda b: set_key(b, WATERMARK_KEY, value))
    assert watermark(kyu_svg(FILLED, tmp_path, config=cfg))[3] == want == grey(float(value))


def test_ac5_watermark_default_without_the_key(tmp_path):
    cfg = config_with(tmp_path, lambda b: drop_key(b, WATERMARK_KEY))
    assert not re.search(rf"^\s*{WATERMARK_KEY}\s*=",
                         award_block(Path(cfg).read_text(encoding="utf-8"), "kyu"), re.M)
    assert watermark(kyu_svg(FILLED, tmp_path, config=cfg))[3] == "#ebebeb"


def test_ac5_crest_false_means_no_watermark(filled, tmp_path):
    cfg = config_with(tmp_path, lambda b: set_key(b, "crest", "false"))
    svg = kyu_svg(FILLED, tmp_path, config=cfg)
    assert watermark(svg) is None and "<circle" not in svg
    assert 'fill-rule="evenodd"' not in svg
    assert printed(svg) == printed(filled)                 # the rest unchanged


# ------------------------------------------------------------------- AC-6 ----
# OQ-2: overlay is the certificate, flat; overlay-flat the same drawing.
def test_ac6_variants(filled, tmp_path):
    got = {v: kyu_svg(FILLED, tmp_path, variant=v) for v in ("overlay", "proof")}
    got["overlay-flat"] = filled
    assert got["overlay"] == got["overlay-flat"]
    for v in ("overlay", "overlay-flat"):
        assert "<image" not in got[v] and guides(got[v]) == []
    assert guides(got["proof"])
    assert printed(got["proof"]) == printed(got["overlay"])
    assert watermark(got["proof"])[:4] == watermark(got["overlay"])[:4]


def test_ac6_no_text_layer_and_no_ink_flag_changes_nothing(tmp_path):
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    bd.main(["-c", EX, "-a", "kyu", "-v", "all", "-f", "svg", *FILLED, f"--out={out_a}"])
    bd.main(["-c", EX, "-a", "kyu", "-v", "all", "-f", "svg", "--no-ink", *FILLED,
             f"--out={out_b}"])
    names = sorted(p.name for p in out_a.iterdir() if p.is_file())
    assert names == sorted(f"kyu-{v}-a4-white-yellow-ヤン-ヤンセン.svg" for v in PLAIN)
    assert _tree(out_a) == _tree(out_b)


# ------------------------------------------------------------------- AC-7 ----
def _zones(svg):
    return [a for t, a in guides(svg)
            if t == "rect" and a["stroke"] == "#e4b9b9" and a["width"] >= 30]


def _slots(svg):
    return [a for t, a in guides(svg)
            if t == "rect" and a["stroke"] == "#e4b9b9" and a["width"] < 12]


@pytest.mark.parametrize("paper", [None, "a3"])
def test_ac7_margins(paper, tmp_path):
    svg = kyu_svg(BLANK + (["--paper", paper] if paper else []), tmp_path, variant="proof")
    g = guides(svg)
    border = [a for t, a in g if a["stroke"] == "#d8c9a8"]
    safe = [a for t, a in g if a["stroke"] == "#cddbe8"]
    assert len(border) == 1 and len(safe) == 1, g
    for (a,), m in ((border, BORDER), (safe, SAFE)):
        assert (a["x"], a["y"]) == pytest.approx((m, m), abs=0.01)
        assert (a["width"], a["height"]) == pytest.approx((W - 2 * m, H - 2 * m), abs=0.01)


def test_ac7_seal_circle_on_the_proof_only(filled, tmp_path):
    proof = kyu_svg(FILLED, tmp_path, variant="proof")
    seals = [a for t, a in guides(proof) if t == "circle"]
    assert len(seals) == 1, seals
    s = seals[0]
    sig = _named_lines(proof)["sig"]
    assert s["cx"] - s["r"] > sig.right + 1.0, (s, sig.right)
    assert s["cy"] == pytest.approx(sig.y, abs=3.0)
    assert 6.0 <= s["r"] <= 12.0
    # Inside the safe inset on every side (AC-7), not only the right.
    assert s["cx"] + s["r"] <= W - SAFE + 0.01, s
    assert s["cy"] + s["r"] <= H - SAFE + 0.01, s
    assert s["cx"] - s["r"] >= SAFE - 0.01 and s["cy"] - s["r"] >= SAFE - 0.01, s
    for svg in (kyu_svg(FILLED, tmp_path, variant="overlay"), filled):
        assert not re.search(r"<circle [^>]*stroke=\"#e4b9b9\"", svg)
        assert len(re.findall(r"<circle ", svg)) == 2          # the watermark's rings


@pytest.mark.parametrize("args, name_zone, grade_zone, slots", [
    (BLANK, 1, 1, 9),
    (["-n", NAME, "-r", "", "-d", ""], 0, 1, 9),
    (["-n", "", "-r", "5", "-d", DATE], 1, 0, 0),
    (FILLED, 0, 0, 0),
], ids=["blank", "name", "grade-date", "filled"])
def test_ac7_calligrapher_zones(args, name_zone, grade_zone, slots, tmp_path):
    svg = kyu_svg(args, tmp_path, variant="proof")
    zones = _zones(svg)

    def covers(a, y):
        return a["y"] <= y <= a["y"] + a["height"]

    names = [a for a in zones if covers(a, MOCK["name"][0])]
    grades = [a for a in zones if covers(a, MOCK["grade"][0])]
    assert len(zones) == name_zone + grade_zone, zones
    assert (len(names), len(grades)) == (name_zone, grade_zone), zones
    for a in zones:
        assert a["x"] + a["width"] / 2 == pytest.approx(W / 2, abs=1.0), a
    got = _slots(svg)
    assert len(got) == slots, got
    if slots:
        date = by_text(svg)["西暦年月日"]
        for a in got:
            assert a["y"] <= date.y <= a["y"] + a["height"], (a, date.y)
            # a slot sits in a gap, clear of the printed 西暦 年 月 日
            for t in date.parts:
                left, right = extent(t)
                assert a["x"] >= right - 0.01 or a["x"] + a["width"] <= left + 0.01, (a, t)


# ------------------------------------------------------------------- AC-8 ----
@pytest.mark.render
@pytest.mark.parametrize("paper", ["a4", "a3"])
def test_ac8_renders_every_variant(paper, home, tmp_path):
    """Also AC-12's totals for `-v all -f pdf,png`, and every grade form's
    characters: 準 in the grade, 十 and 一 in the date (review round 3, R-3)."""
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-v", "all", "-f", "pdf,png", "--dpi", "50",
             "--paper", paper, "-n", NAME, "-r", "white-yellow", "-d", "2026-12-31",
             "--suffix", "t", f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    ev = support.events(r.stdout)
    want = [str(out / f"kyu-{v}-{paper}-t.{e}") for v in PLAIN for e in ("pdf", "png")]
    assert ev[-1] == {"event": "done", "out": str(out), "files": want}
    # AC-12: six steps, pdf and png per variant, no text or ink stage
    progress = [e for e in ev if e["event"] == "progress"]
    assert [(p["step"], p["total"], p["variant"], p["stage"]) for p in progress] == [
        (i + 1, 6, v, s) for i, (v, s) in enumerate(
            (v, s) for v in PLAIN for s in ("pdf", "png"))]
    assert all(set(p) == PROGRESS_KEYS for p in progress)
    pt = A4P_PT if paper == "a4" else A3P_PT
    px = tuple(round(v * 50 / 72) for v in pt)
    for v in PLAIN:
        assert page_size_pt(out / f"kyu-{v}-{paper}-t.pdf") == pytest.approx(pt, abs=0.01)
        mode, a = alpha(out / f"kyu-{v}-{paper}-t.png")
        assert (a.shape[1], a.shape[0]) == px
        # grey only: the overlays carry no colour (DeviceGray); the proof's
        # guides are coloured
        assert mode == ("RGBA" if v == "proof" else "LA"), (v, mode)
    # overlay and overlay-flat: one drawing, the same bytes
    assert (out / f"kyu-overlay-{paper}-t.pdf").read_bytes() == \
        (out / f"kyu-overlay-flat-{paper}-t.pdf").read_bytes()
    # the text, full ink, stays inside the safe inset
    _, a = alpha(out / f"kyu-overlay-{paper}-t.png")
    k = 50 / 25.4 * (1.0 if paper == "a4" else S2)
    ys, xs = (a > 160).nonzero()
    assert xs.min() >= (SAFE - 1) * k and xs.max() <= (W - SAFE + 1) * k
    assert ys.min() >= (SAFE - 1) * k and ys.max() <= (H - SAFE + 1) * k


def _watermark_pixels(png, w):
    """Pixels at the alpha a grey of `w` over white gives (± 6)."""
    target = (255 - round(255 * (1 - w))) * 255 / (255 - bd.INK_GREY)
    _, a = alpha(png)
    return int(((a >= target - 6) & (a <= target + 6)).sum())


@pytest.mark.render
def test_ac8_watermark_prints_light(home, tmp_path):
    """At 50 dpi a pixel is 0.26 mm²; the mon alone is about 2000 mm²."""
    def render(cfg, name):
        out = tmp_path / name
        r = run(["-c", cfg, "-a", "kyu", "-f", "png", "--dpi", "50", *FILLED,
                 "--suffix", "t", f"--out={out}"], home, tmp_path)
        assert r.returncode == 0, r.stderr
        return out / "kyu-overlay-a4-t.png"
    on = render(EX, "on")
    off = render(config_with(tmp_path, lambda b: set_key(b, "crest", "false"), name="off.toml"),
                 "off")
    darker = render(config_with(tmp_path, lambda b: set_key(b, WATERMARK_KEY, "0.2"),
                                name="dark.toml"), "dark")
    per_mm2 = (50 / 25.4) ** 2
    # measured on a prototype: about 3100 mm² with it, 120 without (the
    # anti-aliased edges of the text)
    assert _watermark_pixels(on, WATERMARK) >= 1500 * per_mm2
    assert _watermark_pixels(off, WATERMARK) <= 400 * per_mm2
    assert _watermark_pixels(darker, 0.2) >= 1500 * per_mm2


# ------------------------------------------------------------------- AC-9 ----
# Everything a horizontal sheet prints is checked against Noto Serif JP, the
# face it is printed in; what it does not draw is not checked.
MINCHO = "Noto Serif JP"


def test_ac9_a_mincho_character_prints_on_kyu(tmp_path):
    """𠮷 is in Noto Serif JP and not in Yuji Boku: fine on the kyū sheet,
    refused on the dan sheet."""
    svg = kyu_svg(["-n", "𠮷田", "-r", "5", "-d", DATE], tmp_path)
    assert "𠮷田殿" in texts_of(svg)
    msg = fails(["-a", "dan", "-n", "𠮷田", "-r", "5", "-d", DATE], tmp_path=tmp_path)
    assert "U+20BB7" in msg and "Yuji Boku" in msg and "--name" in msg, msg


@pytest.mark.parametrize("ch", ["한", "⁄"])
def test_ac9_name_checked_against_mincho(ch, tmp_path):
    """한 is in neither face; ⁄ (U+2044) is in Yuji Boku only: both are
    refused on the kyū sheet, naming Noto Serif JP."""
    msg = fails(["-a", "kyu", "-n", f"ヤン{ch}", "-d", DATE], tmp_path=tmp_path)
    assert f"U+{ord(ch):04X}" in msg and MINCHO in msg and "--name" in msg, msg


@pytest.mark.parametrize("where, edit, source", [
    ("heading", lambda b: b.replace(HEADING, "級位한定証"), "the heading of [[awards]] 'kyu'"),
    ("body", lambda b: set_key(b, BODY_KEY, toml_list(["上記の者は한", BODY[1]])), "body"),
])
def test_ac9_award_text_checked_against_mincho(where, edit, source, home, tmp_path):
    cfg = config_with(tmp_path, edit)
    out = tmp_path / "out"
    r = run(["-c", cfg, "-a", "kyu", "-d", DATE, f"--out={out}", "--json"], home, tmp_path)
    ev = support.events(r.stdout)
    assert r.returncode == 1 and [e["event"] for e in ev] == ["error"], ev
    msg = ev[0]["message"]
    assert "U+D55C" in msg and source in msg and MINCHO in msg and "'kyu'" in msg, msg
    assert not out.exists()


def test_ac9_what_the_sheet_draws_decides(tmp_path):
    text = _example().replace('text = "柔能制剛"', 'text = "柔能한剛"')
    cfg = write_config(tmp_path, with_award(
        text, "kyu", lambda b: set_key(b, "formula", '"右한定ス"')))
    # the precept and the formula are not on a horizontal sheet
    assert texts_of(kyu_svg(FILLED, tmp_path, config=cfg)) == FILLED_LINES
    assert "[motto] text" in fails(["-a", "dan", "-d", DATE], config=cfg, tmp_path=tmp_path)
    # the crest ring is, in the watermark, unless crest = false
    text = _example().replace('crest_ring = "〇〇道場"', 'crest_ring = "한한한한"')
    cfg = write_config(tmp_path, text, "ring.toml")
    assert "[dojo] crest_ring" in fails(["-a", "kyu", "-d", DATE], config=cfg,
                                        tmp_path=tmp_path)
    cfg = write_config(tmp_path, with_award(text, "kyu", lambda b: set_key(b, "crest", "false")),
                       "noring.toml")
    assert texts_of(kyu_svg(FILLED, tmp_path, config=cfg)) == FILLED_LINES


# ------------------------------------------------------------------ AC-10 ----
def grade_on(svg):
    """The grade line: the largest text on a sheet printed without a name."""
    return max(lines(svg), key=lambda l: l.size).text


# The grade forms on the kyū sheet and the `purple` refusal are kyu-grades'
# test_ac7_kyu_rank_forms and test_ac8_unknown_kyu_rank_names_the_forms, which
# read the grade off this sheet (review round 3, R-5).
def test_ac10_each_award_its_unit(tmp_path):
    got = svgs(["-a", "dan,kyu", "-n", "", "-r", "3", "-d", DATE], tmp_path)
    assert grade_on(got["kyu"]) == "三級"
    assert "三段" in "".join(re.findall(r">(.)</text>", got["dan"]))


@pytest.mark.parametrize("column", ["true", '"dan"', "false"])
def test_ac10_the_unit_decides_the_sheet(column, tmp_path):
    """User approval, OQ-3: only a kyū award is horizontal.  The same block
    counting in dan, or without a grade, is a vertical landscape sheet."""
    text = with_award(_example(), "kyu", lambda b: set_key(b, "grade_column", column))
    cfg = write_config(tmp_path, with_award(text, "kyu", lambda b: set_key(
        b, "formula", '"右認定ス"')))
    svg = kyu_svg(["-n", "", "-r", "5", "-d", DATE], tmp_path, config=cfg)
    assert page_mm(svg) == (420.0, 297.0)
    assert watermark(svg) is None or watermark(svg)[3] == bd.INK
    assert bd.FONT_BODY in svg


# ------------------------------------------------------------------ AC-11 ----
def _config_error(cfg, home, tmp_path):
    """The message of a configuration error, from the command line: a plain
    run and --list, each one `error` event under --json.  One case per key
    goes this way (body, watermark, motto); the value tables are
    checked in-process with _load_error (review round 3, R-8)."""
    for extra in ([], ["--list"]):
        r = run(["-c", cfg, "-a", "dan", *extra, "--json"], home, tmp_path)
        assert r.returncode == 1, extra
        ev = support.events(r.stdout)
        assert [e["event"] for e in ev] == ["error"], ev
    return ev[0]["message"]


def _load_error(cfg):
    """config.load()'s SystemExit message, the text main() reports."""
    with pytest.raises(SystemExit) as e:
        config_mod.load(cfg)
    assert isinstance(e.value.code, str), e.value.code
    return e.value.code


@pytest.mark.parametrize("value", ['"上記の者は"', "[]", '[""]', "[1]",
                                   toml_list(["一", "二", "三", "四"]),
                                   '[" "]', toml_list(["上記の者は", "\u3000"])])
def test_ac11_bad_body(value, tmp_path):
    cfg = config_with(tmp_path, lambda b: set_key(b, BODY_KEY, value))
    msg = _load_error(cfg)
    for want in (cfg, BODY_KEY, "'kyu'"):
        assert want in msg, (want, msg)


@pytest.mark.parametrize("value", ['"0.08"', "true", "0", "-0.1", "1.5"])
def test_ac11_bad_watermark(value, tmp_path):
    cfg = config_with(tmp_path, lambda b: set_key(b, WATERMARK_KEY, value))
    msg = _load_error(cfg)
    for want in (cfg, WATERMARK_KEY, "'kyu'"):
        assert want in msg, (want, msg)


@pytest.mark.parametrize("value", ["false", "true"])
@pytest.mark.parametrize("slug", ["kyu", "dan"])
def test_ac11_motto_is_an_error(slug, value, tmp_path):
    """User approval, OQ-3: `motto` existed for the vertical kyū sheet and
    is removed; a configuration that sets it is told so, on any award."""
    cfg = config_with(tmp_path, lambda b: set_key(b, MOTTO_KEY, value), slug=slug)
    msg = _load_error(cfg)
    for want in (cfg, MOTTO_KEY, f"'{slug}'"):
        assert want in msg, (want, msg)


def test_ac11_the_050_example_is_refused(home, tmp_path):
    """Its kyū block sets motto = false: an error naming it, not a sheet;
    the `motto` key's case on the command line (--list, --json)."""
    msg = _config_error(EX_050, home, tmp_path)
    assert EX_050 in msg and MOTTO_KEY in msg and "'kyu'" in msg, msg


@pytest.mark.parametrize("value", ['"vertical"', '"horizontal"', '"diagonal"'])
def test_ac11_a_layout_key_is_ignored(value, tmp_path):
    """Never released: an unknown key, ignored like `colour`."""
    cfg = config_with(tmp_path, lambda b: set_key(b, LAYOUT_KEY, value))
    assert kyu_svg(FILLED, tmp_path, config=cfg) == kyu_svg(FILLED, tmp_path)


@pytest.mark.parametrize("key, value", [(BODY_KEY, "[]"), (WATERMARK_KEY, "true")])
def test_ac11_checked_on_a_vertical_award_too(key, value, home, tmp_path):
    """Agreement 5: validated on every award, then ignored where vertical.
    The `body` and `watermark` keys' cases on the command line."""
    cfg = config_with(tmp_path, lambda b: set_key(b, key, value), slug="dan")
    msg = _config_error(cfg, home, tmp_path)
    assert cfg in msg and key in msg and "'dan'" in msg, msg


def test_ac11_body_lines_as_given(tmp_path):
    body = ["右の者は当道場の審査に合格したので", "ここに認定する"]
    cfg = config_with(tmp_path, lambda b: set_key(b, BODY_KEY, toml_list(body)))
    assert texts_of(kyu_svg(FILLED, tmp_path, config=cfg))[3:5] == body
    one = ["上記の者を認定します"]
    cfg = config_with(tmp_path, lambda b: set_key(b, BODY_KEY, toml_list(one)), name="one.toml")
    assert texts_of(kyu_svg(FILLED, tmp_path, config=cfg))[3:4] == one


def test_ac11_a_050_kyu_block_without_motto(tmp_path):
    """OQ-6: the 0.5.0 block with its `motto = false` line taken out (its
    formula still there, no body) prints the approved body text."""
    cfg = config_with(tmp_path, lambda b: drop_key(b, MOTTO_KEY),
                      base=Path(EX_050).read_text(encoding="utf-8"))
    svg = kyu_svg(FILLED, tmp_path, config=cfg)
    assert texts_of(svg) == FILLED_LINES                    # no 右認定ス
    assert watermark(svg) is None                           # its crest = false stands


def test_ac11_formula_optional_on_kyu_only(tmp_path):
    cfg = config_with(tmp_path, lambda b: drop_key(b, "formula"))
    assert "formula" not in award_block(Path(cfg).read_text(encoding="utf-8"), "kyu")
    assert texts_of(kyu_svg(FILLED, tmp_path, config=cfg)) == FILLED_LINES
    cfg = config_with(tmp_path, lambda b: drop_key(b, "formula"), slug="dan", name="dan.toml")
    assert "missing 'formula'" in _load_error(cfg)


def test_ac11_save_round_trip(tmp_path):
    c = config_mod.load(EX)
    path = config_mod.save(c, str(tmp_path / "saved" / "dojo.toml"))
    back = config_mod.load(path)
    assert back.awards == c.awards
    saved = Path(path).read_text(encoding="utf-8")
    kyu = award_block(saved, "kyu")
    for key in (BODY_KEY, WATERMARK_KEY):
        assert re.search(rf"^{key} = ", kyu, re.M), (key, kyu)
    assert not re.search(rf"^(?:{MOTTO_KEY}|{LAYOUT_KEY}|formula) =", kyu, re.M), kyu
    for slug in ("dan", "shihan", "renshi"):
        assert not re.search(rf"^(?:{LAYOUT_KEY}|{MOTTO_KEY}|{BODY_KEY}|{WATERMARK_KEY}) =",
                             award_block(saved, slug), re.M), slug
    args = ["-a", "all", "-n", NAME, "-r", "5", "-d", DATE]
    a, b = svgs(args, tmp_path), svgs(args, tmp_path, config=path)
    assert a == b and set(a) == {"dan", "shihan", "renshi", "kyu"}
    # and a blank kyū proof (from kyu-grades' round trip, review round 3, R-4)
    args = ["-n", "", "-r", "white-yellow", "-d", ""]
    assert kyu_svg(args, tmp_path, variant="proof") == \
        kyu_svg(args, tmp_path, config=path, variant="proof")


def test_ac11_save_without_a_kyu_award_unchanged(tmp_path):
    """A configuration without a kyū award saves as 0.5.0 saved it."""
    path = config_mod.save(config_mod.load(landscape_050(tmp_path)),
                           str(tmp_path / "s" / "dojo.toml"))
    assert support.sha256(Path(path).read_bytes()) == PINS["save_without_kyu"]


# ------------------------------------------------------------------ AC-12 ----
PROGRESS_KEYS = {"event", "step", "total", "award", "variant", "stage", "label"}


@pytest.mark.render
def test_ac12_json_events(home, tmp_path):
    """OQ-11: no ink, so no text or ink stage; the events are the same kinds
    with the same fields."""
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "kyu", "-d", DATE, f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    f = str(out / "kyu-overlay-a4-sample.pdf")
    assert ev == [
        {"event": "progress", "step": 1, "total": 1, "award": "kyu", "variant": "overlay",
         "stage": "pdf", "label": "kyu overlay: writing the PDF"},
        {"event": "file", "path": f},
        {"event": "done", "out": str(out), "files": [f]}]
# `-a kyu -v all -f pdf,png` (six steps): test_ac8_renders_every_variant.  The
# example's default run (ten steps, kyū's `pdf` last):
# test_ac_plain_white.py::test_ac4_default_run (review round 3, R-2, R-3).


# ------------------------------------------------------------------ AC-13 ----
def test_ac13_the_landscape_awards_unchanged(tmp_path):
    """dan, shihan and renshi draw from the new example exactly what they
    draw from 0.5.0's, every variant (-v all) for each set of arguments.
    Without the ink (review round 3, R-1): the inked overlay's bytes are
    pinned by the regression goldens' `inked` cases, run on this example
    without kyū (and kyu-grades' test_ac14 runs the flat cases on the
    example as it is)."""
    old = landscape_050(tmp_path)
    for i, args in enumerate((["-n", NAME, "-r", "2", "-d", DATE], BLANK, ["-d", DATE],
                              ["-n", NAME, "-r", "2", "-d", DATE, "--paper", "a4"])):
        trees = []
        for cfg in (EX, old):
            out = tmp_path / f"ac13-{i}-{len(trees)}"
            bd.main(["-c", cfg, "-a", "dan,shihan,renshi", "-v", "all", "-f", "svg",
                     "--no-ink", *args, f"--out={out}"])
            trees.append(_tree(out))
        assert trees[0] == trees[1] and len(trees[0]) == 3 * len(PLAIN), (args, list(trees[0]))


# ------------------------------------------------------------------ AC-14 ----
@pytest.mark.slow
@pytest.mark.render
def test_ac14_installed_wheel(installed, home, tmp_path):
    exe = [str(installed["menkyo"])]
    site = next(installed["venv"].glob("lib/python*/site-packages"))
    ex = str(site / "menkyo" / "example.toml")
    r = run(["--example-config"], home, tmp_path, exe=exe)
    assert r.returncode == 0 and f"{WATERMARK_KEY} = 0.08" in r.stdout
    r = run(["-c", ex, "--list"], home, tmp_path, exe=exe)
    assert r.stdout.splitlines()[-1] == "kyu-overlay-a4-sample.pdf"
    # the portal's form
    r = run([f"--config={ex}", "--awards=kyu", "--variants=overlay", "--formats=pdf,svg",
             f"--name={NAME}", "--rank=white-yellow", f"--date={DATE}", "--json"],
            home, tmp_path, exe=exe)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
    docs = home / "Documents" / "Menkyo"
    stem = docs / "kyu-overlay-a4-white-yellow-ヤン-ヤンセン"
    assert support.events(r.stdout)[-1] == {"event": "done", "out": str(docs),
                                            "files": [f"{stem}.pdf", f"{stem}.svg"]}
    assert page_size_pt(f"{stem}.pdf") == pytest.approx(A4P_PT, abs=0.01)
    assert texts_of(Path(f"{stem}.svg").read_text(encoding="utf-8")) == FILLED_LINES
    # a character Noto Serif JP lacks: one error, nothing written
    r = run([f"--config={ex}", "--awards=kyu", "--name=ヤン한", "--json"], home, tmp_path,
            exe=exe)
    ev = support.events(r.stdout)
    assert r.returncode == 1 and [e["event"] for e in ev] == ["error"]
    assert MINCHO in ev[0]["message"]
    # a rank a kyū award does not take: one error (was kyu-grades' wheel
    # test, review round 3, R-6)
    r = run(["-c", ex, "-a", "kyu", "--rank=purple", "--json"], home, tmp_path, exe=exe)
    ev = support.events(r.stdout)
    assert r.returncode == 1 and [e["event"] for e in ev] == ["error"], ev
    assert "--rank purple" in ev[0]["message"], ev


# ------------------------------------------------------------------ AC-15 ----
def _readme():
    return (support.REPO / "README.md").read_text(encoding="utf-8")


def _decisions():
    return (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")


def _section(text, heading):
    part = text.split(f"\n## {heading}\n", 1)
    assert len(part) == 2, heading
    return part[1].split("\n## ", 1)[0]


def test_ac15_readme():
    text = _readme()
    row = next(l for l in text.splitlines() if l.startswith("| `--paper"))
    assert re.search(r"portrait", row, re.I) and re.search(r"ky[uū]", row, re.I), row
    config = _section(text, "Configuring it for your dōjō")
    assert re.search(rf"^{BODY_KEY} = \[", config, re.M)
    assert not re.search(rf"^(?:{LAYOUT_KEY}|{MOTTO_KEY}) = ", config, re.M)
    assert re.search(rf"^{WATERMARK_KEY} = 0\.08", config, re.M)
    kyu = config.split('slug = "kyu"', 1)[1].split("```", 1)[0]
    assert not re.search(r"^(?:crest|motto) = false", kyu, re.M), kyu
    variants = _section(text, "Variants")
    assert re.search(r"ky[uū]", variants, re.I), variants
    printing = _section(text, "Printing")
    assert re.search(r"watermark", printing, re.I) and re.search(r"test print", printing, re.I)
    assert re.search(r"portrait", printing, re.I)
    looks = _section(text, "How it looks the way it does")
    assert re.search(r"ky[uū]", looks, re.I) and "Noto Serif JP" in looks
    para = text.split("A character the fonts do not have", 1)[1].split("\n\n", 1)[0]
    assert re.search(r"ky[uū]", para, re.I) and "Noto Serif JP" in para, para


def test_ac15_decisions_entry():
    text = _decisions()
    entries = house_style.decisions_entries(text)
    last = entries[-1]
    heading = last.splitlines()[0]
    assert re.match(r"^## \d{4}-\d{2}-\d{2} – ", heading), heading
    assert re.search(r"ky[uū]", heading, re.I), heading
    flat = " ".join(last.split())
    for want in ("A4", "portrait", "Noto Serif JP", "watermark", "8 %", "0.6.0",
                 BODY_KEY, WATERMARK_KEY, MOTTO_KEY):
        assert want in flat, want
    assert re.search(r"horizontal|yokogaki|横書き", flat), flat[:200]
    for title in ("Kyū grades, on a simpler sheet", "A4 as well as A3"):
        assert title in flat, title


def test_ac15_history_unchanged():
    """Every entry up to and including the 0.5.0 kyū entry, byte for byte."""
    blocks = house_style.decisions_blocks(_decisions())
    pins = PINS["decisions_blocks"]
    assert len(blocks) == len(pins) + 1, [b.splitlines()[0] for b in blocks[len(pins):]]
    changed = [f"block {i}: {blocks[i].splitlines()[0]!r}" for i, h in enumerate(pins)
               if house_style.entry_hash(blocks[i]) != h]
    assert changed == []


def test_ac15_open_items():
    _, open_ = _decisions().split("\n## Open\n", 1)
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    assert not [i for i in items if i.startswith("A second brush font")], items
    for kept in ("An annotated version in Dutch", "A smaller footprint",
                 "Confirm the katakana transcription"):
        assert [i for i in items if i.startswith(kept)], (kept, items)


def test_ac15_recipient_explainer():
    text = (support.REPO / "docs" / "kyu-explained.md").read_text(encoding="utf-8")
    for want in (HEADING, BODY[0], BODY[1], "準", "If you are adapting this document"):
        assert want in text, want
    assert "右認定ス" not in text            # the horizontal sheet has no formula
    assert MOTTO not in text
    assert re.search(r"crest|watermark", text, re.I)


# ------------------------------------------------------------------ AC-16 ----
# 0.6.0 (OQ-12) in pyproject.toml and `menkyo --version`:
# test_ac_render_without_inkscape.py::test_ac37_version (EXPECTED_VERSION),
# the one version check (review round 3, R-4).
