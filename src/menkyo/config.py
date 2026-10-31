"""Certificate configuration: who is issuing this, and with what margins.

Everything that identifies a school -- the name of the art, the name of the
dōjō, the crest ring, the signatory, the awards on offer -- lives in a TOML
file rather than in the code, so that adapting this to another dōjō is a
matter of editing text and never of editing Python.

Search order, first hit wins:

    1. --config PATH
    2. dojo.toml in the per-user data directory  (any copy, checkout included;
                                                  written by config.save())
    3. dojo.toml beside this repository's root   (a checkout only; git-ignored)
    4. example.toml inside the package           (shipped placeholders)

The shipped example uses 〇〇 throughout -- the ordinary Japanese
placeholder, "maru-maru" -- so an unconfigured build produces a certificate
that claims nothing and belongs to nobody.  It does fill every slot, though:
[sample] supplies a stand-in recipient, grade and date so that a first run
shows a finished sheet rather than a mostly empty one.  Clearing that section
gives back the blank slots a calligrapher would fill in.
"""

import json
import os
import tomllib
from dataclasses import dataclass, field

from . import paths

USER_CONFIG = os.path.join(paths.user_data_dir(), "dojo.toml")
LOCAL_CONFIG = (os.path.join(paths.checkout_root(), "dojo.toml")
                if paths.checkout_root() else None)
EXAMPLE_CONFIG = paths.resource("example.toml")

SCHEMA = 1

# The sheets a certificate can be printed on.  `[paper] size` picks the
# dōjō's default for the landscape sheets and --paper overrides it for a run,
# for every award; the kyū sheet is portrait, and A4 unless --paper says
# otherwise.  build_diploma knows their millimetres.
PAPER_SIZES = ("a3", "a4")
DEFAULT_PAPER = "a3"


# What `grade_column` takes besides true and false: the unit a grade is
# counted in.  true is "dan", as it was before kyū awards existed.
UNITS = ("dan", "kyu")

# The kyū sheet's text where the dan sheet has its formula: one string per
# printed line, as the dōjō breaks them (Japanese has no spaces to break at).
DEFAULT_BODY = ("上記の者は本会所定の審査に合格したので", "ここに認定します")
MAX_BODY_LINES = 3
# The kyū sheet's crest, printed as a watermark behind the body: its grey as
# a fraction of black, 0.08 being #ebebeb.
DEFAULT_WATERMARK = 0.08


@dataclass
class Award:
    """One kind of document: its heading, and what it says.

    `unit` is what --rank counts in (a key of UNITS), and it decides the
    sheet: an award counting in kyū is the horizontal A4 portrait sheet,
    which prints `body` instead of the `formula` and its crest as a
    watermark of grey `watermark`; every other award is the vertical
    landscape sheet.  An award without a grade column still reads an
    explicit --rank, in dan.  `crest` false leaves the crest off either
    sheet.
    """
    slug: str
    heading: str
    formula: str
    grade_column: bool = False
    unit: str = "dan"
    crest: bool = True
    body: tuple = ()
    watermark: float = DEFAULT_WATERMARK

    @property
    def horizontal(self):
        """Whether this is the kyū sheet, read in horizontal rows."""
        return self.unit == "kyu"


@dataclass
class Config:
    art: str = "〇〇流柔術"
    dojo: str = "〇〇道場"
    crest_ring: str = ""
    crest_traced: bool = False
    signer_title: str = "師範"
    signer_name: str = ""
    honorific: str = "殿"
    motto: str = ""
    # The sheet, a key of PAPER_SIZES.  The margins below are millimetres of
    # the A3 layout; on A4 they scale with everything else.
    paper_size: str = DEFAULT_PAPER
    # Whether the file says so, for --help; a3 either way when it does not.
    paper_size_set: bool = False
    stock_border: float = 22.0
    safe_inset: float = 38.0
    # Fraction of the page height added to every printed column's starting
    # point -- 0.0 reproduces the original, hand-tuned layout exactly. A large
    # value can push the blank date grid (the tallest column, when the date is
    # left for the calligrapher) past `safe_inset`; check `-v proof`.
    text_drop: float = 0.0
    awards: list = field(default_factory=list)
    source: str = "<defaults>"

    # [sample]: what --name / --rank / --date / --suffix fall back to when the
    # flag is absent.  The shipped example fills these so that a first build
    # shows every slot printed; a real configuration clears them, and the
    # slots go back to being blank for the calligrapher.  A flag given as ''
    # clears one for a single run.
    sample_name: str = ""
    sample_rank: str = ""
    sample_date: str = ""
    sample_suffix: str = ""

    @property
    def slugs(self):
        return [a.slug for a in self.awards]

    def award(self, slug):
        for a in self.awards:
            if a.slug == slug:
                return a
        raise KeyError(slug)


def _shown(value):
    """A value from the file as TOML would write it, for a message.  A TOML
    date or time is not JSON, so it is shown as its own text."""
    return json.dumps(value, ensure_ascii=False, default=str)


def default_path():
    """The config that would be used if --config is not given."""
    for path in (USER_CONFIG, LOCAL_CONFIG):
        if path and os.path.exists(path):
            return path
    return EXAMPLE_CONFIG


def load(path=None):
    path = os.path.abspath(path or default_path())
    if not os.path.exists(path):
        raise SystemExit(
            f"no configuration at {path}\n"
            f"start from `menkyo --example-config > dojo.toml` and edit it, "
            f"or pass --config")
    try:
        with open(path, "rb") as fh:
            raw = tomllib.load(fh)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise SystemExit(f"{path}: {e}")

    schema = raw.get("schema", SCHEMA)
    if schema != SCHEMA:
        raise SystemExit(
            f"{path}: schema = {schema}, but this build understands {SCHEMA}")

    def section(name):
        got = raw.get(name, {})
        if not isinstance(got, dict):
            raise SystemExit(f"{path}: [{name}] should be a table")
        return got

    dojo, art = section("dojo"), section("art")
    signer, recipient = section("signer"), section("recipient")
    motto, paper = section("motto"), section("paper")
    sample = section("sample")

    cfg = Config(
        art=art.get("name", Config.art),
        dojo=dojo.get("name", Config.dojo),
        crest_ring=dojo.get("crest_ring", Config.crest_ring),
        crest_traced=bool(dojo.get("traced_glyphs", Config.crest_traced)),
        signer_title=signer.get("title", Config.signer_title),
        signer_name=signer.get("name", Config.signer_name),
        honorific=recipient.get("honorific", Config.honorific),
        motto=motto.get("text", Config.motto),
        stock_border=float(paper.get("border", Config.stock_border)),
        safe_inset=float(paper.get("safe_inset", Config.safe_inset)),
        text_drop=float(paper.get("text_drop", Config.text_drop)),
        sample_name=str(sample.get("name", Config.sample_name)),
        sample_rank=str(sample.get("rank", Config.sample_rank)),
        sample_date=str(sample.get("date", Config.sample_date)),
        sample_suffix=str(sample.get("suffix", Config.sample_suffix)),
        source=path,
    )

    # Case does not matter ("A4" is how everybody writes it); the file names
    # and everything after this say it in lower case.
    size = paper.get("size", Config.paper_size)
    if not isinstance(size, str) or size.lower() not in PAPER_SIZES:
        raise SystemExit(
            f"{path}: [paper] size = {_shown(size)} is "
            f"not a paper size; use " + " or ".join(f'"{s}"' for s in PAPER_SIZES))
    cfg.paper_size = size.lower()
    cfg.paper_size_set = "size" in paper

    awards = raw.get("awards", [])
    if not awards:
        raise SystemExit(f"{path}: no [[awards]] defined -- there is nothing to print")
    seen = set()
    for i, a in enumerate(awards):
        for key in ("slug", "heading"):
            if not a.get(key):
                raise SystemExit(f"{path}: [[awards]] #{i + 1} is missing '{key}'")
        where = f"{path}: [[awards]] {a['slug']!r}"
        # true and false as before, or the unit by name ("dan" is true).
        # Anything else is a mistake: 1 or "yes" read as true until 0.5.0.
        # Read before the formula, since the unit says whether one is needed.
        column = a.get("grade_column", False)
        if isinstance(column, str) and column.lower() in UNITS:
            grade_column, unit = True, column.lower()
        elif isinstance(column, bool):
            grade_column, unit = column, "dan"
        else:
            raise SystemExit(
                f"{where}: grade_column = {_shown(column)} "
                f"is not a grade column; use true, false, "
                + " or ".join(f'"{u}"' for u in UNITS))
        # The kyū sheet prints its body instead; any other sheet needs one.
        if unit != "kyu" and not a.get("formula"):
            raise SystemExit(f"{path}: [[awards]] #{i + 1} is missing 'formula'")
        if a["slug"] in seen:
            raise SystemExit(f"{path}: two awards share the slug '{a['slug']}'")
        seen.add(a["slug"])
        # 0.5.0's `motto = false` moved every column of the sheet 10 mm left.
        # Ignored, it would move them back without a word, so it is refused.
        if "motto" in a:
            raise SystemExit(
                f"{where}: motto = {_shown(a['motto'])}: the key was removed in "
                f"0.6.0, so delete the line. The precept prints on every "
                f"vertical sheet when [motto] text has one, never on the kyū "
                f"sheet")
        crest = a.get("crest", True)
        if not isinstance(crest, bool):
            raise SystemExit(
                f"{where}: crest = {_shown(crest)} should be true or false")
        # `body` and `watermark` are the kyū sheet's, and checked on every
        # award, so a mistake shows before the award is turned into one.
        body = _body(a.get("body", DEFAULT_BODY), where)
        watermark = _watermark(a.get("watermark", DEFAULT_WATERMARK), where)
        # Any other key -- an award colour from before the plain white sheet,
        # say -- is ignored, so an older configuration keeps working.
        horizontal = unit == "kyu"
        cfg.awards.append(Award(
            slug=a["slug"],
            heading=a["heading"],
            formula=a.get("formula", ""),
            grade_column=grade_column,
            unit=unit,
            crest=crest,
            body=body if horizontal else (),
            watermark=watermark if horizontal else DEFAULT_WATERMARK,
        ))

    # A crest ring of four characters is what the geometry is spaced for; the
    # arc simply looks wrong with more, so say so rather than drawing it badly.
    if cfg.crest_ring and len(cfg.crest_ring) > 5:
        raise SystemExit(
            f"{path}: dojo.crest_ring is {len(cfg.crest_ring)} characters. "
            f"The lower arc holds four comfortably and five at a squeeze.")
    return cfg


def _body(value, where):
    """`body` as a tuple of one to three printed lines, or an error."""
    ok = (isinstance(value, (list, tuple)) and 1 <= len(value) <= MAX_BODY_LINES
          and all(isinstance(v, str) and v.strip() for v in value))
    if not ok:
        raise SystemExit(
            f"{where}: body = {_shown(value)} should be a list of one to "
            f"three lines of text, one string per printed line, "
            f"none of them empty")
    return tuple(value)


def _watermark(value, where):
    """`watermark` as a float above 0 and up to 1, or an error.  A bool is a
    number to Python, and refused here."""
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 < value <= 1):
        raise SystemExit(
            f"{where}: watermark = {_shown(value)} should be a number above 0 "
            f"and up to 1, the crest's grey as a fraction of black (0.08)")
    return float(value)


def _q(value):
    """A TOML basic string.  JSON's escapes are a subset of TOML's."""
    return json.dumps(str(value), ensure_ascii=False)


def save(cfg, path=USER_CONFIG):
    """Write `cfg` as a configuration file that load() reads back.

    Comments in a hand-edited file are not preserved, and [sample] is left
    out: a saved configuration is a real dōjō's, whose blank slots stay blank.
    """
    out = [
        "# Written by menkyo.  Safe to edit by hand.",
        f"schema = {SCHEMA}",
        "",
        "[art]", f"name = {_q(cfg.art)}", "",
        "[dojo]",
        f"name = {_q(cfg.dojo)}",
        f"crest_ring = {_q(cfg.crest_ring)}",
        f"traced_glyphs = {str(cfg.crest_traced).lower()}", "",
        "[signer]",
        f"title = {_q(cfg.signer_title)}",
        f"name = {_q(cfg.signer_name)}", "",
        "[recipient]", f"honorific = {_q(cfg.honorific)}", "",
        "[motto]", f"text = {_q(cfg.motto)}", "",
        "[paper]",
        f"size = {_q(cfg.paper_size)}",
        f"border = {cfg.stock_border}",
        f"safe_inset = {cfg.safe_inset}",
        f"text_drop = {cfg.text_drop}", "",
    ]
    for a in cfg.awards:
        # The newer keys only where they say something, so a configuration
        # without a kyū award saves as it did before them.  A kyū award has
        # no formula to write unless it was given one, and always its body
        # and watermark.
        column = (_q(a.unit) if a.grade_column and a.unit != "dan"
                  else str(a.grade_column).lower())
        out += ["[[awards]]",
                f"slug = {_q(a.slug)}",
                f"heading = {_q(a.heading)}"]
        if a.formula or not a.horizontal:
            out.append(f"formula = {_q(a.formula)}")
        out.append(f"grade_column = {column}")
        if not a.crest:
            out.append("crest = false")
        if a.horizontal:
            out += [f"body = [{', '.join(_q(line) for line in a.body)}]",
                    f"watermark = {a.watermark}"]
        out += [""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    os.replace(tmp, path)
    return path
