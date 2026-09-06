"""Certificate configuration: who is issuing this, and on what paper.

Everything that identifies a school -- the name of the art, the name of the
dōjō, the crest ring, the signatory, the awards on offer -- lives in a TOML
file rather than in the code, so that adapting this to another dōjō is a
matter of editing text and never of editing Python.

Search order, first hit wins:

    1. --config PATH
    2. dojo.toml beside this repository's root   (yours; git-ignored)
    3. config/example.toml                       (shipped placeholders)

The shipped example uses 〇〇 throughout -- the ordinary Japanese
placeholder, "maru-maru" -- so an unconfigured build produces a certificate
that claims nothing and belongs to nobody.  It does fill every slot, though:
[sample] supplies a stand-in recipient, grade and date so that a first run
shows a finished sheet rather than a mostly empty one.  Clearing that section
gives back the blank slots a calligrapher would fill in.
"""

import os
import tomllib
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

LOCAL_CONFIG = os.path.join(ROOT, "dojo.toml")
EXAMPLE_CONFIG = os.path.join(ROOT, "config", "example.toml")

SCHEMA = 1


@dataclass
class Award:
    """One kind of document: its heading, its operative sentence, its colour."""
    slug: str
    heading: str
    formula: str
    grade_column: bool = False
    colour: str = "#8a6a33"


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
    stock_border: float = 22.0
    safe_inset: float = 38.0
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


def default_path():
    """The config that would be used if --config is not given."""
    return LOCAL_CONFIG if os.path.exists(LOCAL_CONFIG) else EXAMPLE_CONFIG


def load(path=None):
    path = os.path.abspath(path or default_path())
    if not os.path.exists(path):
        raise SystemExit(
            f"no configuration at {path}\n"
            f"copy config/example.toml to dojo.toml and edit it, or pass --config")
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

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
        sample_name=str(sample.get("name", Config.sample_name)),
        sample_rank=str(sample.get("rank", Config.sample_rank)),
        sample_date=str(sample.get("date", Config.sample_date)),
        sample_suffix=str(sample.get("suffix", Config.sample_suffix)),
        source=path,
    )

    awards = raw.get("awards", [])
    if not awards:
        raise SystemExit(f"{path}: no [[awards]] defined -- there is nothing to print")
    seen = set()
    for i, a in enumerate(awards):
        for key in ("slug", "heading", "formula"):
            if not a.get(key):
                raise SystemExit(f"{path}: [[awards]] #{i + 1} is missing '{key}'")
        if a["slug"] in seen:
            raise SystemExit(f"{path}: two awards share the slug '{a['slug']}'")
        seen.add(a["slug"])
        cfg.awards.append(Award(
            slug=a["slug"],
            heading=a["heading"],
            formula=a["formula"],
            grade_column=bool(a.get("grade_column", False)),
            colour=a.get("colour", Award.colour),
        ))

    # A crest ring of four characters is what the geometry is spaced for; the
    # arc simply looks wrong with more, so say so rather than drawing it badly.
    if cfg.crest_ring and len(cfg.crest_ring) > 5:
        raise SystemExit(
            f"{path}: dojo.crest_ring is {len(cfg.crest_ring)} characters. "
            f"The lower arc holds four comfortably and five at a squeeze.")
    return cfg
