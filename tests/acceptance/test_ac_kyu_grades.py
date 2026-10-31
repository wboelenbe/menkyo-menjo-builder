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

kyu-redesign (its 'Test changes', user approval 2026-10-30) replaced the
vertical kyū sheet with a horizontal A4 portrait one and removed the `motto`
key: the tests that pinned the vertical kyū layout are gone, and the grade
is read off either sheet (printed_rank).  Its own tests pin the new sheet.
"""

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

SHIPPED = EX = str(support.EXAMPLE)
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
def _shipped():
    return support.EXAMPLE.read_text(encoding="utf-8")


def _example():
    return Path(EX).read_text(encoding="utf-8")


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


def _portrait(svg):
    m = re.search(r'<svg [^>]*width="([\d.]+)mm" height="([\d.]+)mm"', svg)
    return float(m[1]) < float(m[2])


def printed_rank(svg):
    """The grade printed with no name on the sheet: on a landscape sheet the
    column at X_RANK; on the kyū sheet (portrait, kyu-redesign) the text in
    ink of the grade's size (22 mm there, the heading being 16), left to
    right."""
    if not _portrait(svg):
        return column(svg, bd.X_RANK, tol=16.0)
    ts = [(float(m[1]), float(m[3]), m[4]) for m in re.finditer(
        r'<text x="([-\d.]+)" y="([-\d.]+)" [^>]*font-size="([\d.]+)" fill="#111111"'
        r'[^>]*>(.*?)</text>', svg)]
    big = [t for t in ts if t[1] > 18.5]
    return "".join(t[2] for t in sorted(big))


def kyu_rank(value, tmp_path, slug="kyu", config=EX):
    svg = svg_of(slug, ["-n", "", "-d", "", "-r", value], tmp_path, config=config)
    return printed_rank(svg)


def y_rank():
    return bd.Y_RANK + 0.05 * bd.PAGE_H         # the example's text_drop


def _tree(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()} if root.exists() else {}


# ------------------------------------------------------------------- AC-1 ----
def test_ac1_example_has_the_kyu_award():
    c = config_mod.load(SHIPPED)
    assert c.slugs == AWARDS                                    # OQ-5: appended
    kyu = c.award("kyu")
    # kyu-redesign: the shipped kyū award is horizontal, prints a body, not
    # the formula, and keeps its crest (as a watermark); its own AC-1 pins
    # that.  The heading and the unit stay.
    assert kyu.heading == KYU_HEADING
    block = award_block(_shipped(), "kyu")
    assert re.search(rf'^\s*{UNIT_KEY}\s*=\s*"kyu"', block, re.M), block       # OQ-1
    # the three that were there are untouched in what they say
    for slug, heading, formula in (("dan", "段位免状", "右授与ス"),
                                   ("shihan", "師範免許状", "右免許ス"),
                                   ("renshi", "錬士免許状", "右免許ス")):
        a = c.award(slug)
        assert (a.heading, a.formula) == (heading, formula)


# (--example-config: kyu-redesign's test_ac1_example_config_prints_it)


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
    # the default and --all listings: kyu-redesign's test_ac2_default_listing
    assert listing(["-a", "all", "--paper", "a4"], home, tmp_path) == [
        f"{a}-overlay-a4-sample.pdf" for a in AWARDS]


# The rank as the suffix; the other names are kyu-redesign's test_ac2_names.
NAME_CASES = [
    (["-a", "kyu", "-r", "white-yellow"], ["kyu-overlay-a4-white-yellow.pdf"]),
    (["-a", "kyu", "-r", "5"], ["kyu-overlay-a4-5.pdf"]),
    (["-a", "kyu", "-r", "準五級", "--paper", "a4"], ["kyu-overlay-a4-準五級.pdf"]),
]


@pytest.mark.parametrize("args, names", NAME_CASES, ids=[" ".join(c[0]) for c in NAME_CASES])
def test_ac2_names(args, names, home, tmp_path):
    assert listing(args, home, tmp_path) == names


# (planned events: kyu-redesign's test_ac2_planned_events)


# ------------------------------------------------------------------- AC-3 ----
# (the vertical kyū sheet's columns: removed by kyu-redesign)


# ------------------------------------------------------------------- AC-4 ----
# (OQ-3 B's 10 mm shift went with the motto key, kyu-redesign)
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


def test_ac4_an_empty_precept_moves_nothing(tmp_path):
    """A dōjō without a precept (`[motto] text = ""`) keeps every dan column
    where it was."""
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
# kyu-redesign: the kyū cases went with the vertical kyū sheet.
@pytest.mark.parametrize("slug, value, grade", [
    ("dan", "Shihan", "Shihan"), ("dan", "2", "二段"),
    ("shihan", "師範代", "師範代")])
@pytest.mark.parametrize("name", ["", NAME])
def test_ac4_grade_stays_in_its_zone(slug, value, grade, name, tmp_path):
    svg = svg_of(slug, ["-n", name, "-r", value, "-d", ""], tmp_path)
    x_rank = bd.right_columns(True)[1] if name else bd.X_RANK
    rank = sorted(_split(svg, x_rank, 0.0)["rank"], key=lambda t: t[1])
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
# ------------------------------------------------------------------- AC-6 ----
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


# (a mixed run, each in its unit: kyu-redesign's test_ac10_each_award_its_unit)


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
    # (the proof's grade zone on the kyū sheet: kyu-redesign's AC-7)
    kyu = svg_of("kyu", ["-n", "", "-d", "", "-r", ""], tmp_path, variant="proof")
    assert printed_rank(kyu) == ""


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
        ["mudansha-overlay-a4-sample.pdf"]                 # kyu-redesign OQ-1
    # and an award called kyu that declares dan counts in dan
    # (it then needs the formula a landscape sheet prints)
    text = with_award(_example(), "kyu", lambda b: set_key(set_key(b, UNIT_KEY, "true"),
                                                           "formula", '"右認定ス"'))
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


# kyu-redesign removed the motto key (an error now, its AC-11)
@pytest.mark.parametrize("key", [CREST_KEY])
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


# (the save round trip: kyu-redesign's test_ac11_save_round_trip)


def test_ac11_save_writes_new_keys_only_where_needed(tmp_path):
    """Agreement 6: grade_column is "kyu" only for a kyū award, true/false
    otherwise; crest and motto are written only when false.  A config with
    no kyū award saves byte for byte as 0.4.0 did."""
    c = config_mod.load(EX)
    text = Path(config_mod.save(c, str(tmp_path / "a" / "dojo.toml"))).read_text(encoding="utf-8")
    kyu, dan = award_block(text, "kyu"), award_block(text, "dan")
    assert re.search(rf'^{UNIT_KEY} = "kyu"$', kyu, re.M), kyu
    # (crest and motto false on the kyū award: gone with kyu-redesign)
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


# kyu-redesign: the kyū sheet prints in Noto Serif JP, which has 𠮷, so the
# character neither face has is 한; the formula is not printed there.  The
# heading's check: kyu-redesign's test_ac9_award_text_checked_against_mincho.
def test_ac12_kyu_formula_and_rank_checked_first(home, tmp_path):
    r, ev, out = _glyph_fail(["-a", "kyu", "--rank=한級"], EX, home, tmp_path)
    assert r.returncode == 1 and "--rank" in ev[0]["message"] and "U+D55C" in ev[0]["message"]
    assert not out.exists()


# ------------------------------------------------------------------ AC-13 ----
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
    bd.main(["-c", SHIPPED, *case["argv"], f"--out={out}"])
    files = {golden_lib.sized(n): sha for n, sha in golden["files"].items()}
    written = sorted(p.name for p in out.iterdir() if p.is_file())
    assert sorted(n for n in written if not n.startswith("kyu-")) == sorted(files)
    assert [n for n in written if n.startswith("kyu-")], written
    for name, sha in files.items():
        want = golden_lib.sized(golden_lib.blob(sha))
        assert (out / name).read_text(encoding="utf-8") == want, name


def test_ac14_baseline_copy_is_the_example_without_kyu():
    text = _shipped()
    stripped = golden_lib.baseline_awards_only(text)
    assert 'slug = "kyu"' in text and 'slug = "kyu"' not in stripped
    for slug in ("dan", "shihan", "renshi"):
        assert award_block(stripped, slug) == award_block(text, slug)
    assert stripped.split("[[awards]]", 1)[0] == text.split("[[awards]]", 1)[0]
    assert stripped.split("\n[sample]\n", 1)[1] == text.split("\n[sample]\n", 1)[1]


# ------------------------------------------------------------------ AC-15 ----
# (the installed wheel, the `purple` refusal included: kyu-redesign's
# test_ac14_installed_wheel)


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
    # the configuration example shows the kyū award and its unit
    # (kyu-redesign: no longer crest = false and motto = false, its AC-15)
    assert re.search(r'^slug = "kyu"', text, re.M)
    assert re.search(rf'^{UNIT_KEY} = "kyu"', text, re.M)
    # the glyph-check paragraph no longer says the art is always on the ring
    para = text.split("A character the fonts do not have", 1)[1].split("\n\n", 1)[0]
    assert re.search(r"ky[uū]|without a crest|no crest|crest = false", para), para
    assert re.search(r"ky[uū]", text.split("## Quick start", 1)[0], re.I), \
        "the introduction does not mention kyū certificates"


def test_ac16_example_comments():
    """[sample] rank's comment says what the sample is on a kyū sheet."""
    sample = _shipped().split("\n[sample]\n", 1)[1]
    rank_comment = sample.split("rank =", 1)[0].rsplit("\n\n", 1)[-1]
    assert "五級" in rank_comment, rank_comment


def test_ac16_decisions_entry():
    text = _decisions()
    body, open_ = text.split("\n## Open\n", 1)
    entries = house_style.decisions_entries(text)
    # kyu-redesign added an entry after this one: found by its heading
    last = next(e for e in entries
                if e.startswith("## 2026-10-29 – Kyū grades, on a simpler sheet\n"))
    for want in (KYU_HEADING, KYU_FORMULA, "準", "white-yellow", UNIT_KEY, "0.5.0"):
        assert want in last, want
    # what it overrides, by title: the precept on every document, and every
    # unrecognised --rank passing through
    flat = " ".join(last.split())
    for title in ("Purple menkyo, and a precept column", "Printing the three hand slots"):
        assert title in flat, title
    # (the earlier entries, pinned: house-style-sweep's test_ac11_history_pinned
    # and kyu-redesign's test_ac15_history_unchanged)
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    assert not [i for i in items if re.search(r"ky[uū]", i, re.I)], items
    assert [i for i in items if i.startswith("An annotated version in Dutch")], items


# OQ-8, recommended: an explainer for the recipient, like the other three
# (kyu-redesign's test_ac15_recipient_explainer).


# ------------------------------------------------------------------ AC-17 ----
# OQ-9, recommended: a new award and new --rank behaviour make 0.5.0.
# kyu-redesign (its OQ-12) made it 0.6.0, checked by
# test_ac_render_without_inkscape.py::test_ac37_version.
