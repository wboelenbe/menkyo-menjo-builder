"""
Japanese martial-arts certificates: dan and kyū grades and teaching licences.

Generates the certificate's text and crest, to be printed on plain white
paper, landscape: A3, or A4 with ``--paper a4`` (the same layout scaled by
1/√2), the configuration's ``[paper] size`` choosing which by default.  The
three things a calligrapher would brush in — the rank, the recipient, the
date numerals — can each be printed or left empty; ``--rank``, ``--name`` and ``--date``
decide, falling back to the ``[sample]`` stand-ins in the configuration and
cleared for a run by passing ``''``.

Which documents exist, and whose name goes on them, is configuration: see
``example.toml`` and ``config.py``.  Nothing in this file names a
school.  An award counts its grade in dan or in kyū, and may leave out the
crest and the precept column, as the example's kyū certificate does.

One file per award per variant, written as ``<award>-<variant>-<size>.<ext>``
(``dan-overlay-a3.pdf``, with any suffix after the size) into ./build from a
checkout, ~/Documents/Menkyo otherwise.  The variants are one
layout, plus a fallback and a check:

    overlay        the certificate, its text graded like sumi — the one to print
    overlay-flat   solid black instead of graded sumi, pure vector
    proof          safe areas and the zones the calligrapher fills

Only ``overlay`` is built by default, as PDF.

    menkyo                        the sensible default
    menkyo --list                 show what that is
    menkyo -a dan -v proof -f png one proof sheet
    menkyo --all -f pdf,png       everything

``--help`` documents the rest, and ``--json`` turns the output into one JSON
object per line -- progress, files, errors -- for a program running this one.
"""

import argparse
import json
import math
import os
import re
import shutil
import sys
import unicodedata

from . import __version__, ink, paths
from . import config as config_mod
from . import render as renderer

# Output directory; main() replaces it when --out is given.
BUILD = paths.default_output_dir()

# Who is issuing this, and on what paper. Replaced in main() by whatever
# --config selects; the placeholder defaults keep the module importable and
# name no school.
CFG = config_mod.Config()

# ---------------------------------------------------------------- page ------
PAGE_W, PAGE_H = 420.0, 297.0          # A3 landscape, mm: the layout's own units

# The sheets it prints on, landscape, in mm (config.PAPER_SIZES names them).
# A4 is not a layout of its own: it is the A3 one scaled by 1/√2, every
# column, margin and the crest alike (DECISIONS.md).  A4 is not exactly A3
# over √2 (297/420 against 210/297), so the scaled layout, anchored at the
# top left, is 0.02 mm short of the A4 width and 0.01 mm over its height:
# both at the edges, inside the margins, where nothing prints.
PAPERS = {"a3": (420.0, 297.0), "a4": (297.0, 210.0)}
SCALE = {"a3": 1.0, "a4": 1 / math.sqrt(2)}
DEFAULT_PAPER = config_mod.DEFAULT_PAPER

INK = "#111111"                        # near-black, reads as sumi in print
INK_GREY = int(INK[1:3], 16)           # the same, as a grey level (it is one)

# Yuji Boku (佑字 木) — a genuinely brush-written kaisho by Kinuta Font
# Factory, OFL, vendored in fonts/ inside this package.  It is what makes the
# printed columns read as sumi rather than as type.  The crest ring stays a
# mincho: a mon is a carved seal, not brushwork, and the firmer face survives
# being 5 mm across.  These are family names; render.FONTS maps each to its
# file in fonts/ (the crest's to Noto Serif JP SemiBold).
FONT_BODY = renderer.BODY
FONT_CREST = renderer.CREST
FONT_DIR = renderer.FONT_DIR   # for reading only: render.FONT_DIR is the one used
W_REG, W_MED, W_BOLD = 400, 500, 600

# ------------------------------------------------------------- typography ---
# Baseline sits ~0.38 em below the visual centre of a CJK em box.
BASELINE_DROP = 0.38
SMALL_KANA = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
ROTATE_IN_VERTICAL = set("ー〜（）「」『』")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def vcol(chars, x, y0, size, weight=W_MED, pitch=None, fill=INK, letter_gap=0.0):
    """One vertical column of glyphs, top-down, centred on x.

    `chars` may contain None for a blank slot the calligrapher fills in.
    Returns (svg, y_of_last_glyph_centre).
    """
    pitch = pitch if pitch is not None else size * (1.0 + letter_gap)
    out = []
    cy = y0
    for ch in chars:
        if ch is not None:
            dx, dy = 0.0, 0.0
            if ch in SMALL_KANA:               # sits upper-right of the em box
                dx, dy = 0.085 * size, -0.085 * size
            bx, by = x + dx, cy + dy + BASELINE_DROP * size
            extra = ""
            if ch in ROTATE_IN_VERTICAL:       # long vowel mark turns 90°
                extra = f' transform="rotate(90 {x:.3f} {cy:.3f})"'
            out.append(
                f'<text x="{bx:.3f}" y="{by:.3f}" font-family="{FONT_BODY}" '
                f'font-weight="{weight}" font-size="{size:.3f}" fill="{fill}" '
                f'text-anchor="middle"{extra}>{esc(ch)}</text>'
            )
        cy += pitch
    return "\n".join(out), cy - pitch


# ------------------------------------------------------------------ crest ---
# A yotsume-bishi ("four eyes in lozenges") mon inside a double ring. The
# yotsume-bishi is a traditional Japanese kamon, not anybody's property; the
# proportions below were measured off one rendering of it and normalised to
# the outer ring's centreline radius. Adjust them if your own crest differs.
R_OUTER = 1.0
R_INNER = 0.662
RING_STROKE = 0.0256
MON_HALF = 0.594          # overall half-diagonal of the yotsume-bishi
MON_SUB = 0.2804          # half-diagonal of each of the four lozenges
MON_DIST = 0.3137         # centre-to-centre distance of a lozenge
MON_HOLE = 0.0688         # half-diagonal of the square hole in each lozenge
GLYPH_R = 0.826           # radius the ring kanji sit on
GLYPH_SIZE = 0.256        # em size of the ring kanji


def _diamond(cx, cy, h):
    return f"M {cx:.4f} {cy-h:.4f} L {cx+h:.4f} {cy:.4f} L {cx:.4f} {cy+h:.4f} L {cx-h:.4f} {cy:.4f} Z"


def _traced_path(ch):
    """Where a traced crest glyph for `ch` would be: crest/ beside the config."""
    return os.path.join(os.path.dirname(CFG.source), "crest", f"{ch}.svg")


def _traced_glyph(ch):
    """Path data + viewBox for one crest glyph, if a vector trace is supplied.

    Off unless `traced_glyphs` is set under [dojo]. Drop `<character>.svg`
    — a potrace trace of the lettering on your own crest — into a crest/
    folder beside the configuration file, and the ring uses your outlines
    instead of the font's.

    Not the default, and worth a look before you turn it on: display lettering
    is usually drawn already distorted to fit its arc, and tracing it puts a
    second arc on top of the first. At 5 mm the typeset ring is normally the
    more legible of the two. Returns None when there is no such file.
    """
    path = _traced_path(ch)
    if not os.path.exists(path):
        return None
    src = open(path).read()
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src)
    if not vb:
        return None
    w, h = float(vb.group(1)), float(vb.group(2))
    return w, h, re.findall(r'<path d="(.*?)"', src, re.S)


def crest(cx, cy, radius, ring_bottom=None, ring_top=None, fill=INK):
    """The crest: a yotsume-bishi mon inside a double ring.

    ring_bottom / ring_top are 4- and 5-character strings laid along the
    lower and upper arcs, read right to left (clockwise from lower right).
    """
    S = radius
    g = [f'<g transform="translate({cx:.3f} {cy:.3f})">']
    sw = RING_STROKE * S
    g.append(f'<circle r="{R_OUTER*S:.3f}" fill="none" stroke="{fill}" stroke-width="{sw:.3f}"/>')
    g.append(f'<circle r="{R_INNER*S:.3f}" fill="none" stroke="{fill}" stroke-width="{sw:.3f}"/>')

    # mon: four lozenges N/E/S/W, each pierced by a small lozenge
    d = []
    for dx, dy in ((0, -MON_DIST), (MON_DIST, 0), (0, MON_DIST), (-MON_DIST, 0)):
        d.append(_diamond(dx * S, dy * S, MON_SUB * S))
        d.append(_diamond(dx * S, dy * S, MON_HOLE * S))
    g.append(f'<path d="{" ".join(d)}" fill="{fill}" fill-rule="evenodd"/>')

    def place(text, angles, outward=False):
        for ch, ang in zip(text, angles):
            import math
            a = math.radians(ang)
            gx, gy = GLYPH_R * S * math.cos(a), GLYPH_R * S * math.sin(a)
            # lower arc: glyph top points at the centre; upper arc: away from it.
            rot = ang + 90.0 if outward else ang - 90.0
            tr = _traced_glyph(ch) if CFG.crest_traced else None
            if tr:
                w, h, paths = tr
                k = GLYPH_SIZE * S / max(w, h)
                inner = "".join(f'<path d="{p}" fill="{fill}"/>' for p in paths)
                g.append(
                    f'<g transform="translate({gx:.3f} {gy:.3f}) rotate({rot:.2f}) '
                    f'scale({k:.5f}) translate({-w/2:.3f} {-h/2:.3f}) '
                    f'translate(0 {h:.3f}) scale(0.1 -0.1)">{inner}</g>'
                )
            else:
                sz = GLYPH_SIZE * S
                g.append(
                    f'<g transform="translate({gx:.3f} {gy:.3f}) rotate({rot:.2f})">'
                    f'<text x="0" y="{BASELINE_DROP*sz:.3f}" font-family="{FONT_CREST}" '
                    f'font-weight="{W_BOLD}" font-size="{sz:.3f}" fill="{fill}" '
                    f'text-anchor="middle">{esc(ch)}</text></g>'
                )

    # Both arcs read right to left, i.e. clockwise on screen: the first
    # character sits at the lower right and the last at the lower left.
    if ring_bottom:
        n, step = len(ring_bottom), 34.0
        place(ring_bottom, [90 - step * (n - 1) / 2 + i * step for i in range(n)])
    if ring_top:
        n, step = len(ring_top), 30.0
        place(ring_top, [-90 + step * (n - 1) / 2 - i * step for i in range(n)],
              outward=True)

    g.append("</g>")
    return "\n".join(g)


# ----------------------------------------------------------------- layout ---
# Column x positions, right to left, in mm. Taken from the proportions of a
# traditional 賞状 and rebalanced for A3 with a single signatory.
X_HEADING = 352.0       # printed: names the award — 段位免状 / 師範免許状 …
X_NAME_1 = 322.0        # hand: given name  (Latin, rotated)
X_RANK = 310.0          # hand: rank / licence, e.g. 二段
X_NAME_2 = 298.0        # hand: family name (Latin, rotated)

# With --name the recipient is printed in katakana instead of brushed in Latin,
# so the name takes a column of its own.  Recipient before award, right to
# left, as a 賞状 reads; the columns are then spaced by right_columns() rather
# than pinned, because a licence has one column fewer than a dan diploma.
X_VERB = 253.0          # printed: 右授与ス / 右免許ス
X_DATE = 205.0          # printed + hand: 西暦 ____ 年 __ 月 __ 日
X_STYLE = 163.0         # printed: the art        [art] name
X_DOJO = 137.0          # printed: the dōjō      [dojo] name
X_TITLE = 111.0         # printed: the signatory's office  [signer] title
X_SIGNER = 85.0         # printed: the signatory's name    [signer] name

Y_HEADING = 64.0
Y_RANK = 64.0
Y_VERB = 70.0
Y_BLOCK = 92.0

SZ_HEADING = 18.0
SZ_AWARDEE = 16.0       # shrunk to fit if the name is a long one
AWARDEE_MAX_H = 184.0   # mm of column available before the seal line
SZ_RANK = 30.0          # printed rank, when --rank is given


def right_columns(rank_column):
    """x for the recipient, and for the grade, between heading and formula.

    A dan diploma states a grade; a licence names its award in the heading and
    has nothing further to say, so it is one column shorter. Pinning the
    columns left the licence with a hole where the grade would be and the name
    stranded against the edge — so they are spread evenly through the gap
    instead, and the layout closes up on its own when the grade is absent.
    """
    right = X_HEADING - SZ_HEADING / 2.0        # heading's left edge
    left = X_VERB + SZ_VERB / 2.0               # formula's right edge
    widths = [SZ_AWARDEE] + ([SZ_RANK] if rank_column else [])
    gap = (right - left - sum(widths)) / (len(widths) + 1)
    xs, cursor = [], right
    for w in widths:
        cursor -= gap
        xs.append(cursor - w / 2.0)
        cursor -= w
    return xs[0], (xs[1] if rank_column else None)

# First dan is 初段, never 一段.  The rest take plain numerals — 二段 rather
# than the formal 弐段, which is the commoner modern practice.  Pass the
# literal text (--rank 弐段) if you would rather have the formal forms.
DAN_KANJI = {1: "初段", 2: "二段", 3: "三段", 4: "四段", 5: "五段",
             6: "六段", 7: "七段", 8: "八段", 9: "九段", 10: "十段"}
DAN_ROMAJI = {"shodan": 1, "nidan": 2, "sandan": 3, "yondan": 4, "godan": 5,
              "rokudan": 6, "nanadan": 7, "shichidan": 7, "hachidan": 8,
              "kyudan": 9, "kudan": 9, "judan": 10}

# Kyū grades count down: 10 is the first a beginner gets, 1 the last before
# shodan.  ikkyu is 一級 (no 初 on this side).
KYU_KANJI = {n: k + "級" for n, k in zip(range(1, 11), "一二三四五六七八九十")}
KYU_ROMAJI = {"ikkyu": 1, "nikyu": 2, "sankyu": 3, "yonkyu": 4, "gokyu": 5,
              "rokkyu": 6, "nanakyu": 7, "shichikyu": 7, "hachikyu": 8,
              "hakkyu": 8, "kyukyu": 9, "jukkyu": 10, "jikkyu": 10}
# The belt a kyū grade wears, as an input form only: nothing prints it.
BELTS = {"white": 6, "yellow": 5, "orange": 4, "green": 3, "blue": 2,
         "brown": 1}
# The children's steps between two belts, 準 ("associate") with the grade
# they lead to.  Only these three: 準 exists for the in-between belts.
JUN_STEPS = {"white-yellow": 5, "yellow-orange": 4, "orange-green": 3}
_JUN = re.compile(r"jun-?(\d+)")

KYU_FORMS = ("1 to 10, the romaji (ikkyu, nikyu … gokyu … jukkyu), a belt "
             "(" + ", ".join(BELTS) + "), a children's step ("
             + ", ".join(JUN_STEPS) + ", or jun5, jun4, jun3), "
             "or the kanji as it should print (三級)")


def _kyu_number(key):
    """A kyū grade read from lower-case, folded ASCII or digits of any width:
    (n, 準?), or None."""
    if key.isdecimal():
        n = int(key)
        return (n, False) if n in KYU_KANJI else None
    if key in KYU_ROMAJI:
        return KYU_ROMAJI[key], False
    if key in BELTS:
        return BELTS[key], False
    if key in JUN_STEPS:
        return JUN_STEPS[key], True
    m = _JUN.fullmatch(key)
    if m and int(m.group(1)) in JUN_STEPS.values():
        return int(m.group(1)), True
    return None


def _kyu_only(key):
    """Whether folded ASCII is meant as a kyū grade, valid or not: a belt, a
    children's step, jun<n>, or a word ending in kyu.  Whole words only, so
    kyudan is a dan grade."""
    return (key in BELTS or key in JUN_STEPS or bool(_JUN.fullmatch(key))
            or bool(re.fullmatch(r"[a-z0-9-]*kyu", key)))


def rank_kanji(value, unit="dan", source="--rank", award=None):
    """Turn 2, 'nidan' or '二段' into the kanji that goes on the sheet.

    `unit` is the award's (config.UNITS): on a kyū award 5, 'gokyu' and
    'yellow' are 五級 and 'white-yellow' or 'jun5' is 準五級.  `source` and
    `award` (a slug) are for the messages.  ū and uu read as u, so 'jūdan'
    and 'gokyuu' count, and digits are digits full-width too (５).  Anything else still non-ASCII passes through
    untouched, so the licences can use the same flag: --rank 師範.  Other
    ASCII passes through on a dan award (--rank Shihan) unless it is a kyū
    form, and is refused on a kyū award, which has nothing to print it as.
    """
    key = str(value).strip()
    # NFC first, so a ū typed as u + combining macron folds as well.
    folded = unicodedata.normalize("NFC", key)
    folded = folded.replace("ū", "u").replace("Ū", "U")
    folded = re.sub("uu", "u", folded, flags=re.I).lower()
    on = f" on [[awards]] {award!r}" if award else ""
    if unit == "kyu":
        # Digits are read whatever their width (５), as on a dan award.
        if not folded.isascii() and not folded.isdecimal():
            return key                  # literal: 三級, 準五級, 弐級 …
        got = _kyu_number(folded)
        if got is None:
            raise SystemExit(
                f"{source} {value}: not a kyū grade{on}. Use {KYU_FORMS}.")
        n, jun = got
        return ("準" if jun else "") + KYU_KANJI[n]
    n = DAN_ROMAJI.get(folded)
    if n is None and folded.isdecimal():
        n = int(folded)
    if n is None:
        if folded.isascii() and _kyu_only(folded):
            raise SystemExit(
                f"{source} {value}: a kyū grade, but "
                + (f"[[awards]] {award!r}" if award else "this award")
                + " counts in dan; give a dan grade (1 to 10, nidan, 二段) "
                "or the text to print")
        return key                      # literal: 師範, 錬士, 弐段 …
    if n not in DAN_KANJI:
        raise SystemExit(f"{source} {value}: dan grades run from 1 to 10")
    return DAN_KANJI[n]


SZ_VERB = 40.0
SZ_DATE = 11.5
SZ_BLOCK = 14.0
SZ_TITLE = 12.0
SZ_SIGNER = 12.5

CREST_C = (210.0, 50.0)
CREST_R = 19.0

SEAL_C = (85.0, 236.0)
SEAL_R = 11.0

# An optional school precept ([motto] text in the config).  It is not part of
# the ceremonial reading order of heading -> formula -> date -> authority, so
# it sits in its own quiet column to the left rather than crowding one of
# those, and it goes on every document rather than on any particular one.
# Leave it empty and the column simply is not drawn.
X_MOTTO = 57.0
SZ_MOTTO = 11.0

# An award without the precept column (`motto = false`, as on a kyū sheet)
# moves every column and the seal this far left, which centres the printed
# block on the sheet: 68.75 mm clear on the left, 69 on the right.  The
# crest stays at the page's centre.  Keyed on the award, never on an empty
# [motto] text, so a dōjō without a precept keeps the layout it had.
NO_MOTTO_SHIFT = 10.0

# Blank date: 西暦 ____ 年 __ 月 ___ 日.  The day gets three slots, not two —
# 二十一 through 三十一 are three characters, which is most of the month.
DATE_SLOTS = ["西", "暦", None, None, None, None, "年",
              None, None, "月", None, None, None, "日"]

_DIGITS = "〇一二三四五六七八九"


def _kanji_count(n):
    """1-31 the way it is spoken: 十二, 二十, 二十一, 三十一."""
    if n < 10:
        return _DIGITS[n]
    tens, ones = divmod(n, 10)
    return ("" if tens == 1 else _DIGITS[tens]) + "十" + (_DIGITS[ones] if ones else "")


def date_column(value):
    """An ISO date, or 'today', as the diploma's own date column.

    The year is written digit by digit — 二〇二六 — which is what 西暦 takes on
    a Japanese certificate; month and day are spoken numbers.
    """
    import datetime
    if str(value).strip().lower() == "today":
        d = datetime.date.today()
    else:
        try:
            d = datetime.date.fromisoformat(str(value).strip())
        except ValueError:
            raise SystemExit(f"--date {value}: use YYYY-MM-DD, or 'today'")
    year = "".join(_DIGITS[int(c)] for c in str(d.year))
    return list(f"西暦{year}年{_kanji_count(d.month)}月{_kanji_count(d.day)}日")


def document(verb, heading, crest_kind="full", guides=False,
             layer="all", name=None, honorific="殿", rank=None, date=None,
             rank_column=True, sheet=DEFAULT_PAPER, motto_column=True):
    """One certificate. `verb` is the four-character award formula.

    Everything below is drawn in the A3 layout's millimetres.  On another
    `sheet` (a key of PAPERS) the root is that sheet and the layout sits
    inside a scale(); an A3 sheet has no wrapper, so its SVG is what it
    always was.  `crest_kind` None draws no crest; without `motto_column`
    there is no precept and the columns move NO_MOTTO_SHIFT to the left.
    """
    # `[paper] text_drop` (a fraction of the page height) shifts every printed
    # column's starting point down by the same amount, giving the whole
    # reading order more air above it without re-tuning each Y_* constant by
    # hand. It leaves the crest and the seal where they are -- those are not
    # text lines -- and it does not resize anything, so a large value can push
    # a tall column (the blank date grid is the tallest) past `safe_inset`.
    # Check `-v proof` after changing it.
    # A printed grade always has its column, as build_one() asks for it.
    rank_column = rank_column or bool(rank)
    drop = CFG.text_drop * PAGE_H
    y_heading, y_rank, y_verb, y_block = (
        Y_HEADING + drop, Y_RANK + drop, Y_VERB + drop, Y_BLOCK + drop)
    # Every column's x, and the seal's, moved left when there is no precept.
    dx = 0.0 if motto_column else -NO_MOTTO_SHIFT
    x_heading, x_verb, x_date = X_HEADING + dx, X_VERB + dx, X_DATE + dx
    x_awardee, x_rank = right_columns(rank_column)
    x_awardee += dx
    x_rank = (x_rank if name else X_RANK) + dx if rank_column else None
    seal_x = SEAL_C[0] + dx

    o = []
    # The chrome layer is the base of an inked composite, whose text arrives
    # as an <image xlink:href> (_inked_text_image), so it declares xlink.
    xlink = (' xmlns:xlink="http://www.w3.org/1999/xlink"'
             if layer == "chrome" else "")
    sheet_w, sheet_h = PAPERS[sheet]
    o.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"{xlink} '
        f'width="{sheet_w}mm" height="{sheet_h}mm" viewBox="0 0 {sheet_w} {sheet_h}">'
    )
    # The closing tag; build_one() puts the inked text just before "</svg>",
    # outside the scale, since its box is in the sheet's own millimetres.
    end = "</svg>"
    if SCALE[sheet] != 1.0:
        o.append(f'<g transform="scale({SCALE[sheet]:.10f})">')
        end = "</g>\n</svg>"
    if guides and layer != "text":
        sb, si = CFG.stock_border, CFG.safe_inset
        o.append(
            f'<rect x="{sb}" y="{sb}" '
            f'width="{PAGE_W-2*sb}" height="{PAGE_H-2*sb}" '
            f'fill="none" stroke="#d8c9a8" stroke-width="0.4" stroke-dasharray="3 2"/>'
        )
        o.append(
            f'<rect x="{si}" y="{si}" '
            f'width="{PAGE_W-2*si}" height="{PAGE_H-2*si}" '
            f'fill="none" stroke="#cddbe8" stroke-width="0.4" stroke-dasharray="1.5 2"/>'
        )
        # zones the calligrapher fills.  A printed recipient takes its own
        # guide away and shifts the rank's.
        zones = []
        if rank_column and not rank:
            zones.append((x_rank - 16, y_rank - 14, 32, 66, "rank"))
        if not name:
            zones.append((X_NAME_2 + dx - 13, 130, 50, 95, "name"))
        for x, y, w, h, lab in zones:
            o.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
                f'stroke="#e4b9b9" stroke-width="0.4" stroke-dasharray="2 2"/>'
            )
        for i, ch in enumerate([] if date else DATE_SLOTS):
            if ch is None:
                cy = y_block + i * SZ_DATE
                o.append(
                    f'<rect x="{x_date-SZ_DATE*0.42:.2f}" y="{cy-SZ_DATE*0.42:.2f}" '
                    f'width="{SZ_DATE*0.84:.2f}" height="{SZ_DATE*0.84:.2f}" fill="none" '
                    f'stroke="#e4b9b9" stroke-width="0.3" stroke-dasharray="1 1.5"/>'
                )
        o.append(
            f'<circle cx="{seal_x}" cy="{SEAL_C[1]}" r="{SEAL_R}" fill="none" '
            f'stroke="#e4b9b9" stroke-width="0.4" stroke-dasharray="2 2"/>'
        )

    # The crest stays out of the ink pass: a mon is a carved seal pressed in
    # one go, not a brushed stroke, so it should not fade at its thin points.
    if layer == "text":
        pass
    elif crest_kind == "bare":
        o.append(crest(*CREST_C, CREST_R))
    elif crest_kind == "bottom":
        o.append(crest(*CREST_C, CREST_R, ring_bottom=CFG.crest_ring))
    elif crest_kind == "full":
        o.append(crest(*CREST_C, CREST_R, ring_bottom=CFG.crest_ring,
                       ring_top=CFG.art))

    if layer == "chrome":                       # ink layer supplies the text
        o.append(end)
        return "\n".join(o)

    # printed columns
    o.append(vcol(list(heading), x_heading, y_heading, SZ_HEADING, W_BOLD)[0])
    if name:
        chars = list(name) + list(honorific or "")
        size = min(SZ_AWARDEE, AWARDEE_MAX_H / max(1, len(chars)))
        o.append(vcol(chars, x_awardee, y_rank, size, W_BOLD)[0])
    if rank:
        # The column is spaced for two characters (二段, 五級).  A longer
        # grade (準五級, a literal) shrinks into the same 60 mm, from the
        # same top, rather than running down into the name's zone.
        size = min(SZ_RANK, 2 * SZ_RANK / len(rank))
        y0 = y_rank if size == SZ_RANK else y_rank - (SZ_RANK - size) / 2
        o.append(vcol(list(rank), x_rank, y0, size, W_BOLD)[0])
    o.append(vcol(list(verb), x_verb, y_verb, SZ_VERB, W_BOLD)[0])
    # A printed date is set solid; a blank one keeps its slots spaced out so
    # the calligrapher has a grid to write into.
    o.append(vcol(date or DATE_SLOTS, x_date, y_block, SZ_DATE, W_MED)[0])
    # Any of these may be empty in the config, in which case vcol draws
    # nothing and the column is simply absent.
    o.append(vcol(list(CFG.art), X_STYLE + dx, y_block, SZ_BLOCK, W_MED)[0])
    o.append(vcol(list(CFG.dojo), X_DOJO + dx, y_block, SZ_BLOCK, W_MED)[0])
    o.append(vcol(list(CFG.signer_title), X_TITLE + dx, y_block, SZ_TITLE, W_MED)[0])
    o.append(vcol(list(CFG.signer_name), X_SIGNER + dx, y_block, SZ_SIGNER, W_MED)[0])
    if motto_column:
        o.append(vcol(list(CFG.motto), X_MOTTO, y_block, SZ_MOTTO, W_MED)[0])

    o.append(end)
    return "\n".join(o)


# --------------------------------------------------------------- progress ---
# A certificate takes seconds, nearly all of it in a handful of slow steps:
# rendering the text layer, the sumi grading, each export.  Those
# are counted and reported as each one starts, so whoever is waiting -- a
# terminal, or the portal reading --json -- can show "step 3 of 8" instead of
# nothing.
STAGES = {
    "text": "rendering the text",
    "ink": "grading the ink",
    "pdf": "writing the PDF",
    "png": "writing the PNG",
}


class _Progress:
    """Counts a run's slow steps and hands each one to `report` as it starts.

    `report` gets a dict: step and total (step counts from 1, so step ==
    total means the last one is under way), award, variant, stage (a key of
    STAGES) and label, the same in English.
    """

    def __init__(self, total=0, report=None):
        self.total, self.step, self.report = total, 0, report
        self.award = self.variant = ""

    def __call__(self, stage):
        self.step += 1
        if self.report:
            self.report({
                "step": self.step, "total": max(self.total, self.step),
                "award": self.award, "variant": self.variant, "stage": stage,
                "label": f"{self.award} {self.variant}: {STAGES[stage]}"})


# Replaced by main() for every run; the default counts and tells no one.
PROGRESS = _Progress()


def _stages(variant, formats, inked):
    """The slow steps build_one() will report for one variant, in order."""
    out = []
    if inked and VARIANTS[variant].get("inked"):
        out += ["text", "ink"]
    if "pdf" in formats:
        out.append("pdf")
    if "png" in formats:
        out.append("png")
    return out


def _stderr_progress(event):
    print(f"[{event['step']}/{event['total']}] {event['label']}",
          file=sys.stderr, flush=True)


def _emit(event, **data):
    """One line of --json output: a JSON object with an "event" key."""
    print(json.dumps({"event": event, **data}, ensure_ascii=False), flush=True)


# ------------------------------------------------------------------ build ---
INK_DPI = 600.0         # resolution of the inked text raster
MAX_DPI = 2400          # the most --dpi takes for a PNG


def _inked_text_image(base, verb, heading, kw):
    """Render the text layer alone, ink it, and return an <image> element.

    Rendered to the text's own outline box rather than the page: a full A3
    at 600 dpi is mostly empty, and cropping keeps the raster, and the memory
    the ink pass needs for it, to the part that carries text.  The box is in
    the sheet's millimetres, so on A4 the layer is 600 dpi of the A4 sheet
    and the ink keeps its physical grain (DECISIONS.md).
    """
    from PIL import Image

    # Our own render, a few tens of megapixels for an A3 text block, more for
    # a larger sheet. The decompression-bomb guard is meant for untrusted
    # input; it is not one here.
    Image.MAX_IMAGE_PIXELS = None

    PROGRESS("text")
    tmp = base + "-textlayer"
    box = renderer.text_layer(document(verb, heading, layer="text", **kw),
                              tmp + ".png", INK_DPI, ink=INK_GREY)
    if box is None:                     # no text at all: nothing to ink
        return ""
    x, y, w, h = box

    PROGRESS("ink")
    ink.ink_layer(tmp + ".png", tmp + ".png", INK_DPI)
    # xlink:href, not SVG 2's plain href, so that the -f svg file opens with
    # its text in older SVG editors too, which ignore the latter.
    return (f'<image x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
            f'xlink:href="{os.path.basename(tmp)}.png" preserveAspectRatio="none"/>')


def render(svg_path, out_base, formats, dpi=300):
    """Export one intermediate SVG into `out_base` in the requested formats.

    Each stage is announced before its work, and a file is written whole
    under a temporary name and then moved into place, so a caller never
    sees half of one.
    """
    written = []
    with open(svg_path, encoding="utf-8") as fh:
        svg = fh.read()
    base_dir = os.path.dirname(svg_path)
    tmp = svg_path[:-4] + ".part"
    pdf = None

    if "pdf" in formats:
        PROGRESS("pdf")
        pdf, _ = renderer.svg_to_pdf(svg, base_dir)
        with open(tmp, "wb") as fh:
            fh.write(pdf.data)
        os.replace(tmp, out_base + ".pdf")
        written.append(out_base + ".pdf")

    if "png" in formats:
        PROGRESS("png")
        if pdf is None:
            pdf, _ = renderer.svg_to_pdf(svg, base_dir)
        renderer.page_png(pdf, tmp, dpi, ink=INK_GREY)
        os.replace(tmp, out_base + ".png")
        written.append(out_base + ".png")

    if "svg" in formats:
        # An inked SVG references its text raster by relative path, so the
        # raster has to travel with it.
        shutil.copy(svg_path, out_base + ".svg")
        written.append(out_base + ".svg")
        side = svg_path[:-4] + "-textlayer.png"
        if os.path.exists(side):
            shutil.copy(side, out_base + "-textlayer.png")
            written.append(out_base + "-textlayer.png")

    return written


# --------------------------------------------------------------- variants ---
# The awards themselves come from the config ([[awards]]): slug, heading,
# formula, whether the body states a grade and in which unit, and whether
# the sheet has the crest and the precept.
# The heading names the document, so several awards read apart at a glance;
# a grade column is for documents that state a specific grade as well —
# a dan certificate does, a teaching licence usually does not, since its
# heading has already named the award.  --rank overrides that either way.

# Every variant prints on plain white paper; see DECISIONS.md.
VARIANTS = {
    # the certificate, its text graded like sumi: what you print
    "overlay": dict(inked=True),
    # solid-black fallback: the graded text is a greyscale raster, and a home
    # laser halftones grey.  If the columns come out mottled, print this.
    "overlay-flat": dict(),
    # safe areas and the zones the calligrapher fills
    "proof": dict(guides=True),
}

DEFAULT_VARIANTS = ["overlay"]
DEFAULT_FORMATS = ["pdf"]


def _sample_help(sample):
    """The trailing sentence of a fill-in flag's help, given its stand-in."""
    if not sample:
        return "The slot is left blank unless you pass this."
    return (f"Defaults to the config's sample, {sample}; "
            f"pass '' for a blank slot.")


def _fallback(flag, sample):
    """A flag's value, the config's [sample] stand-in, or nothing.

    Leaving the flag off takes the sample; passing it as '' clears the sample
    for one run, which is how you get an empty slot back from a config that
    fills it.
    """
    if flag is None:
        return sample or None
    return flag or None


def _suffix_for(name):
    """A filesystem-friendly tag from a katakana name, for the output files."""
    out = name.replace("・", "-").replace("\u3000", "-")
    out = "-".join(out.split())
    return "".join(c for c in out if c not in '/\\:*?"<>|')


def _stem(slug, variant, sheet, suffix):
    """An output's name without its extension: <award>-<variant>-<size>, then
    the suffix.  The award, variant and size are fixed vocabularies and the
    suffix is free text, so it goes last, where it always was."""
    return f"{slug}-{variant}-{sheet}" + (f"-{suffix}" if suffix else "")


def build_one(slug, heading, verb, variant, formats, dpi=300, inked=True,
              work=None, name=None, honorific="殿", rank=None,
              date=None, suffix="", rank_column=True, sheet=DEFAULT_PAPER,
              crest=True, motto=True):
    kw = dict(VARIANTS[variant])
    kw["rank_column"] = rank_column or bool(rank)
    kw["sheet"] = sheet
    # The award's sheet keys; left out when true, so document() runs as it
    # always did for an award that has both.
    if not crest:
        kw["crest_kind"] = None
    if not motto:
        kw["motto_column"] = False
    if date:
        kw["date"] = date
    if name:
        kw["name"] = name
        kw["honorific"] = honorific
    if rank:
        kw["rank"] = rank
    if not inked:
        kw.pop("inked", None)
    use_ink = kw.pop("inked", False)
    PROGRESS.award, PROGRESS.variant = slug, variant

    stem = _stem(slug, variant, sheet, suffix)
    svg_path = os.path.join(work, stem + ".svg")
    if use_ink:
        img = _inked_text_image(os.path.join(work, stem), verb, heading, kw)
        svg = document(verb, heading, layer="chrome", **kw)
        svg = svg.replace("</svg>", img + "</svg>")
    else:
        svg = document(verb, heading, **kw)
    open(svg_path, "w").write(svg)

    return render(svg_path, os.path.join(BUILD, stem), formats, dpi=dpi)


def _check_glyphs(checks):
    """Stop before anything is drawn if a font lacks a character.

    `checks` is a list of (text, where it came from, font family, traced):
    exactly the strings a run will draw, each with the flag or configuration
    key it came from, so the message can say what to change.  With `traced`,
    a character that has a traced crest/<ch>.svg needs no glyph from the
    font; its path data is read now, so a file the writer cannot draw fails
    here too, naming the file.  The fonts themselves are opened and checked
    first.
    """
    renderer.open_fonts()
    for text, source, family, traced in checks:
        face = renderer.face(family)
        for ch in text:
            glyph = _traced_glyph(ch) if traced else None
            if glyph:
                for d in glyph[2]:
                    try:
                        renderer.path_ops(d)
                    except SystemExit as e:
                        raise SystemExit(f"{_traced_path(ch)}: {e.code}")
                continue
            if not face.has(ch):
                raise SystemExit(renderer.missing_glyph(ch, source, face))


def _glyph_checks(awards, name, name_src, honorific, honorific_src,
                  ranks, rank_src, date, date_src):
    """What _check_glyphs looks at for this run: what will be drawn, only.

    `ranks` maps each award to the grade it prints, or None.
    """
    body, crest = FONT_BODY, FONT_CREST
    sheets = [CFG.award(slug) for slug in awards]
    out = []
    if name:
        out.append((name, name_src, body, False))
        out.append((honorific or "", honorific_src, body, False))
    if date:
        out.append(("".join(date), date_src, body, False))
    else:
        out.append(("".join(c for c in DATE_SLOTS if c), "the blank date column",
                    body, False))
    for text, key in ((CFG.art, "[art] name"), (CFG.dojo, "[dojo] name"),
                      (CFG.signer_title, "[signer] title"),
                      (CFG.signer_name, "[signer] name")):
        out.append((text, key, body, False))
    # the precept and the crest only if an award of this run draws them; the
    # crest ring: the art on the upper arc, crest_ring on the lower
    if any(aw.motto for aw in sheets):
        out.append((CFG.motto, "[motto] text", body, False))
    if any(aw.crest for aw in sheets):
        out.append((CFG.crest_ring, "[dojo] crest_ring", crest, CFG.crest_traced))
        out.append((CFG.art, "[art] name, on the crest ring", crest,
                    CFG.crest_traced))
    for aw in sheets:
        slug = aw.slug
        out.append((aw.heading, f"the heading of [[awards]] {slug!r}", body, False))
        out.append((aw.formula, f"the formula of [[awards]] {slug!r}", body, False))
        if ranks[slug]:
            out.append((ranks[slug], rank_src, body, False))
    return out


def _csv(value, allowed, what):
    if value.strip().lower() == "all":
        return list(allowed)
    picked = [v.strip() for v in value.split(",") if v.strip()]
    bad = [v for v in picked if v not in allowed]
    if bad:
        raise SystemExit(
            f"unknown {what}: {', '.join(bad)}\n"
            f"choose from: {', '.join(allowed)} (or 'all')")
    return picked


class _Parser(argparse.ArgumentParser):
    """argparse, except that under --json a rejected flag is a message.

    Without --json argparse prints its usage and exits 2, as any command
    does.  With it, the message has to reach cli() as a SystemExit("message"),
    like main()'s own, so that it arrives as an "error" event on stdout.
    """

    def __init__(self, *args, json_errors=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_errors = json_errors

    def error(self, message):
        if self.json_errors:
            raise SystemExit(message)
        super().error(message)


def _wants_json(argv):
    """Whether `argv` asks for --json, read the way argparse reads it.

    argparse takes any unambiguous prefix (--js), so looking for the literal
    "--json" is not enough.  No other flag starts with --j, so a parser that
    knows only this one gives the real parser's answer.
    """
    p = _Parser(add_help=False, json_errors=True)
    p.add_argument("--json", action="store_true")
    try:
        return p.parse_known_args(argv)[0].json
    except SystemExit:          # --json=x: the real parser rejects it too
        return True


def main(argv=None, progress=None):
    """Run the generator as the command line would, with `argv` as its flags.

    `progress`, if given, is called with each step's dict (see _Progress);
    without it, progress goes to stderr when that is a terminal.
    """
    global CFG, BUILD, PROGRESS

    # --config has to be resolved before the parser is built, because the
    # awards it lists are what --awards will accept.  The flags that need no
    # configuration are answered here, so a broken one cannot block them.
    as_json = _wants_json(argv)
    pre = _Parser(prog="menkyo", add_help=False, json_errors=as_json)
    pre.add_argument("-c", "--config", metavar="PATH")
    pre.add_argument("--version", action="version", version=f"menkyo {__version__}")
    pre.add_argument("--example-config", action="store_true")
    known, _ = pre.parse_known_args(argv)
    if known.example_config:
        with open(config_mod.EXAMPLE_CONFIG, encoding="utf-8") as fh:
            sys.stdout.write(fh.read())
        return
    CFG = config_mod.load(known.config)
    slugs = CFG.slugs

    ap = _Parser(
        prog="menkyo", json_errors=as_json,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Generate Japanese dan-grade, kyū-grade and "
                    "teaching-licence artwork.",
        epilog=(
            "By default this writes only what you would actually print: the\n"
            "overlay, on plain white A3 or A4, for every award your config\n"
            "defines. Everything else is opt-in. Each file is named\n"
            "<award>-<variant>-<size>[-<suffix>].<ext>, the size a3 or a4.\n"
            "\n"
            f"configuration: {os.path.relpath(CFG.source, os.getcwd())}\n"
            "  start from `menkyo --example-config > dojo.toml` and edit it,\n"
            "  or use --config to choose between several.\n"
            "\n"
            "examples:\n"
            "  menkyo                                    the sensible default\n"
            "  menkyo --list                             show what that is\n"
            f"  menkyo -a {slugs[0]} -v proof -f png             one proof sheet\n"
            "  menkyo --all -f pdf,png                   everything, for an archive\n"))
    ap.add_argument("--version", action="version", version=f"menkyo {__version__}")
    ap.add_argument("-c", "--config", metavar="PATH",
                    help="certificate configuration to use (default: dojo.toml "
                         f"in {paths.user_data_dir()} or, in a checkout, the "
                         "repository root; otherwise the shipped example)")
    ap.add_argument("--example-config", action="store_true",
                    help="print the shipped example configuration, to start "
                         "your own from, and stop")
    ap.add_argument("-a", "--awards", default="all", metavar="LIST",
                    help="comma-separated: " + ",".join(slugs) + " (default: all)")
    ap.add_argument("-v", "--variants", default=",".join(DEFAULT_VARIANTS),
                    metavar="LIST",
                    help="comma-separated: " + ",".join(VARIANTS)
                         + f" (default: {','.join(DEFAULT_VARIANTS)})")
    ap.add_argument("-f", "--formats", default=",".join(DEFAULT_FORMATS),
                    metavar="LIST",
                    help="comma-separated: pdf,png,svg "
                         f"(default: {','.join(DEFAULT_FORMATS)})")
    ap.add_argument("--no-ink", action="store_true",
                    help="skip the sumi grading and set solid black; the same "
                         "thing the -flat variant gives you")
    ap.add_argument("--paper", type=str.lower, choices=config_mod.PAPER_SIZES,
                    metavar="SIZE",
                    help="the sheet, landscape: a3 or a4, the A4 being the A3 "
                         "layout scaled down to fit (default: "
                         f"{CFG.paper_size}, "
                         + ("from [paper] size in the configuration"
                            if CFG.paper_size_set else
                            "as the configuration has no [paper] size")
                         + ")")
    ap.add_argument("--dpi", type=int, default=300, metavar="N",
                    help=f"resolution for PNG output, 1-{MAX_DPI} (default: 300)")
    ap.add_argument("-n", "--name", metavar="KATAKANA",
                    help="print the recipient's name in its own column instead "
                         "of leaving it for the calligrapher, e.g. "
                         "'ヤン・ヤンセン'. Shrinks to fit a long name. "
                         + _sample_help(CFG.sample_name))
    ap.add_argument("-r", "--rank", metavar="GRADE",
                    help="print the grade instead of leaving it for the "
                         "calligrapher, counted in the award's unit. On a dan "
                         "award a number or romaji becomes kanji (2 or nidan "
                         "-> 二段, 1 -> 初段, up to 10); on a kyū award 5, "
                         "gokyu or yellow -> 五級, white-yellow or jun5 -> "
                         "準五級. Kanji are printed as given, so the licences "
                         "can use this too: --rank 師範. "
                         + _sample_help(CFG.sample_rank))
    ap.add_argument("-d", "--date", metavar="YYYY-MM-DD",
                    help="print the award date in kanji instead of leaving it "
                         "for the calligrapher; 'today' also works. "
                         "西暦二〇二六年九月五日. "
                         + _sample_help(CFG.sample_date))
    ap.add_argument("--honorific", metavar="TEXT",
                    help="appended to the printed name (default: "
                         f"{CFG.honorific or 'none'}, from the config); "
                         "pass '' to leave it off")
    ap.add_argument("--suffix", metavar="TEXT",
                    help="tag appended to output filenames; defaults to the "
                         "name itself when --name is given, so one recipient's "
                         "files never overwrite another's"
                         + (f" (config: {CFG.sample_suffix})"
                            if CFG.sample_suffix else ""))
    ap.add_argument("--all", action="store_true",
                    help="shorthand for --awards all --variants all")
    ap.add_argument("-o", "--out", metavar="DIR",
                    help=f"directory to write into (default: {BUILD})")
    ap.add_argument("--clean", action="store_true",
                    help="empty the build directory first")
    ap.add_argument("--list", action="store_true",
                    help="list the files that would be written, then stop")
    ap.add_argument("--json", action="store_true",
                    help="for programs running this one: every line on stdout "
                         "is a JSON object -- progress, a file written, done, "
                         "or an error. See the README for the events.")
    args = ap.parse_args(argv)
    # A PNG of zero or fewer pixels is nothing to draw, and at MAX_DPI an A3
    # page is already over a gigapixel.  Checked for every run, --list too,
    # and the same range at either size: --dpi is per inch of the sheet.
    if not 1 <= args.dpi <= MAX_DPI:
        raise SystemExit(f"--dpi {args.dpi}: use a resolution from 1 to {MAX_DPI}")
    if args.out:
        BUILD = os.path.abspath(os.path.expanduser(args.out))

    if args.all:
        args.awards, args.variants = "all", "all"
    awards = _csv(args.awards, slugs, "award")
    variants = _csv(args.variants, list(VARIANTS), "variant")
    formats = _csv(args.formats, ["pdf", "png", "svg"], "format")

    # A flag left off falls back to the config's [sample]; a flag given as ''
    # clears that fallback for this run and leaves the slot blank again.
    name = _fallback(args.name, CFG.sample_name)
    raw_rank = _fallback(args.rank, CFG.sample_rank)
    raw_date = _fallback(args.date, CFG.sample_date)
    # A sample grade belongs only on the documents that state one. Printing it
    # on a licence would put 五段 on a sheet whose heading has already named
    # the award -- so the sample is gated on grade_column (and not even read
    # where it is not drawn), while an explicit --rank still goes on whatever
    # you asked for (--rank 師範).  Each award reads the value in its own
    # unit: -r 3 is 三段 on a dan award and 三級 on a kyū one.  Read for the
    # whole run before anything is listed or written.
    sample_rank = args.rank is None and bool(raw_rank)
    rank_src = "--rank" if args.rank is not None else "[sample] rank"
    ranks = {}
    for slug in awards:
        aw = CFG.award(slug)
        drawn = raw_rank and not (sample_rank and not aw.grade_column)
        ranks[slug] = (rank_kanji(raw_rank, aw.unit, rank_src, slug)
                       if drawn else None)
    date = date_column(raw_date) if raw_date else None
    honorific = CFG.honorific if args.honorific is None else args.honorific
    # The filename tag: whatever you asked for, else the config's tag for its
    # own specimens, else the recipient and grade you named -- which is what
    # keeps one recipient's files from overwriting another's. Asking for a
    # recipient or a grade takes the derived tag, sample section or not.
    if args.suffix is not None:          # including '', meaning no tag at all
        suffix = args.suffix
    elif args.name is None and args.rank is None:
        suffix = CFG.sample_suffix       # '' unless a config supplies one
    else:
        parts = [_suffix_for(args.rank) if args.rank else "",
                 _suffix_for(args.name) if args.name else ""]
        suffix = "-".join(p for p in parts if p)
    # The flag wins over the configuration's [paper] size.
    sheet = args.paper or CFG.paper_size

    if args.list:
        for slug in awards:
            for v in variants:
                for ext in formats:
                    n = f"{_stem(slug, v, sheet, suffix)}.{ext}"
                    if args.json:
                        _emit("planned", file=n)
                    else:
                        print(n)
        return

    # Every character drawn must be in its font, and both fonts must open:
    # checked for the whole run before anything is written, or emptied.
    _check_glyphs(_glyph_checks(
        awards, name,
        "--name" if args.name is not None else "[sample] name (no --name given)",
        honorific,
        "--honorific" if args.honorific is not None else "[recipient] honorific",
        ranks, "--rank" if args.rank is not None else "[sample] rank (no --rank given)",
        date,
        "--date" if args.date is not None else "[sample] date (no --date given)"))

    if args.clean and os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD, exist_ok=True)
    work = os.path.join(BUILD, ".work")
    os.makedirs(work, exist_ok=True)

    if args.json:
        def report(event):
            _emit("progress", **event)
    else:
        report = progress or (_stderr_progress if sys.stderr.isatty() else None)
    PROGRESS = _Progress(
        sum(len(_stages(v, formats, not args.no_ink)) * len(awards)
            for v in variants),
        report)

    total = []
    try:
        for slug in awards:
            aw = CFG.award(slug)
            heading, verb = aw.heading, aw.formula
            for variant in variants:
                written = build_one(slug, heading, verb, variant, formats,
                                    dpi=args.dpi, inked=not args.no_ink,
                                    work=work, name=name, honorific=honorific,
                                    rank=ranks[slug], date=date, suffix=suffix,
                                    rank_column=aw.grade_column, sheet=sheet,
                                    crest=aw.crest, motto=aw.motto)
                for w in written:
                    if args.json:
                        _emit("file", path=w)
                    else:
                        print("wrote", w)
                total += written
    finally:
        # The intermediates go whether the run worked or not.
        shutil.rmtree(work, ignore_errors=True)
    if args.json:
        _emit("done", out=BUILD, files=total)
    else:
        print(f"\n{len(total)} file(s) in {BUILD}/")


def cli(argv=None):
    """The `menkyo` command: main(), with failures as JSON events under --json.

    Without --json a failure is a message on stderr and a non-zero exit, as
    from any command.  With it, the same message also arrives as an "error"
    event on stdout, so a caller reading the events needs no second channel:
    every failure, a rejected flag or a traceback included, ends the output
    with exactly one "error" and exit code 1.
    """
    argv = sys.argv[1:] if argv is None else argv
    if not _wants_json(argv):
        return main(argv)
    try:
        main(argv)
    except SystemExit as e:
        if e.code in (None, 0):         # --help, --version: plain text, done
            raise
        # main()'s messages for the user, rejected flags among them
        _emit("error", message=e.code if isinstance(e.code, str)
              else f"exit status {e.code}")
        raise SystemExit(1)
    except Exception as e:              # an unusable --out, a full disk, a bug
        _emit("error", message=f"{type(e).__name__}: {e}")
        raise SystemExit(1)
