#!/usr/bin/env python3
"""
Japanese martial-arts certificates: dan grades and teaching licences.

Generates a *text-only overlay* meant to be printed onto bought Japanese
blank certificate stock (賞状用紙), A3 landscape.  The three things a
calligrapher would brush in — the rank, the recipient, the date numerals —
can each be printed or left empty; ``--rank``, ``--name`` and ``--date``
decide, falling back to the ``[sample]`` stand-ins in the configuration and
cleared for a run by passing ``''``.

Which documents exist, and whose name goes on them, is configuration: see
``config/example.toml`` and ``config.py``.  Nothing in this file names a
school.

One file per award per variant, written as ``<award>-<variant>.<ext>`` into
../build.  The variants are two ways of printing one layout, plus fallbacks:

    overlay        text only, to print onto bought Japanese 賞状用紙
    full           our own engraved border (border.py), for cream stock
    full-cream     the same with the paper tint printed — the one to look at
    overlay-flat   solid black instead of graded sumi, pure vector
    full-flat      likewise, with the border
    proof          safe areas and the zones the calligrapher fills

Only ``overlay`` and ``full-cream`` are built by default, as PDF and PNG:
enough to look at and enough to print, without burying the ones that matter.
``--press`` adds the colour-converted files a commercial printer wants.

    python3 build_diploma.py                        the sensible default
    python3 build_diploma.py --list                  show what that is
    python3 build_diploma.py -a dan -v proof -f png  one proof sheet
    python3 build_diploma.py --all --press           everything

``--help`` documents the rest.
"""

import argparse
import os
import re
import shutil
import subprocess

import border
import config as config_mod
import ink

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")

# Who is issuing this, and on what paper. Replaced in main() by whatever
# --config selects; the placeholder defaults keep the module importable and
# name no school.
CFG = config_mod.Config()

# ---------------------------------------------------------------- page ------
PAGE_W, PAGE_H = 420.0, 297.0          # A3 landscape, mm

INK = "#111111"                        # near-black, reads as sumi in print

# Fallback for the drawn border (border.py), when an award names no colour of
# its own. Only relevant to the `full` / `full-cream` variants — the overlay
# route's border is the bought stock, which we do not control. Giving the
# teaching licences a second colour is a good way to make them read apart from
# the grades at a glance; see the `colour` key in the config.
SEPIA = "#8a6a33"

# Yuji Boku (佑字 木) — a genuinely brush-written kaisho by Kinuta Font
# Factory, OFL, vendored in ../fonts.  It is what makes the printed columns
# read as sumi rather than as type.  The crest ring stays a mincho: a mon is a
# carved seal, not brushwork, and the firmer face survives being 5 mm across.
FONT_BODY = "Yuji Boku"
FONT_CREST = "Noto Serif CJK JP SemiBold"
FONT_DIR = os.path.join(HERE, "..", "fonts")
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


CREST_GLYPH_DIR = os.path.join(HERE, "..", "crest")


def _traced_glyph(ch):
    """Path data + viewBox for one crest glyph, if a vector trace is supplied.

    Off unless `traced_glyphs` is set under [dojo]. Drop `<character>.svg`
    — a potrace trace of the lettering on your own crest — into crest/, and
    the ring uses your outlines instead of the font's.

    Not the default, and worth a look before you turn it on: display lettering
    is usually drawn already distorted to fit its arc, and tracing it puts a
    second arc on top of the first. At 5 mm the typeset ring is normally the
    more legible of the two. Returns None when there is no such file.
    """
    path = os.path.join(CREST_GLYPH_DIR, f"{ch}.svg")
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
              "kyudan": 9, "kudan": 9, "judan": 10, "juudan": 10}


def rank_kanji(value):
    """Turn 2, 'nidan' or '二段' into the kanji that goes on the sheet.

    Anything that is not a dan grade passes through untouched, so the licences
    can use the same flag: --rank 師範.
    """
    key = str(value).strip()
    n = DAN_ROMAJI.get(key.lower())
    if n is None and key.isdigit():
        n = int(key)
    if n is None:
        return key                      # literal: 師範, 錬士, 弐段 …
    if n not in DAN_KANJI:
        raise SystemExit(f"--rank {value}: dan grades run from 1 to 10")
    return DAN_KANJI[n]
SZ_VERB = 40.0
SZ_DATE = 11.5
SZ_BLOCK = 14.0
SZ_TITLE = 12.0
SZ_SIGNER = 12.5

CREST_C = (210.0, 50.0)
CREST_C_BORDERED = (210.0, 58.0)   # clears the drawn band's inner rule
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
             drawn_border=False, paper=None, layer="all", name=None,
             honorific="殿", rank=None, date=None, rank_column=True,
             border_colour=SEPIA):
    """One certificate. `verb` is the four-character award formula."""
    o = []
    o.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}mm" height="{PAGE_H}mm" '
        f'viewBox="0 0 {PAGE_W} {PAGE_H}">'
    )
    if layer != "text":
        if paper:
            o.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="{paper}"/>')
        if drawn_border:
            o.append(border.border_svg(PAGE_W, PAGE_H, colour=border_colour))

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
            x_rank_guide = (right_columns(True)[1] if name else X_RANK)
            zones.append((x_rank_guide - 16, Y_RANK - 14, 32, 66, "rank"))
        if not name:
            zones.append((X_NAME_2 - 13, 130, 50, 95, "name"))
        for x, y, w, h, lab in zones:
            o.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
                f'stroke="#e4b9b9" stroke-width="0.4" stroke-dasharray="2 2"/>'
            )
        for i, ch in enumerate([] if date else DATE_SLOTS):
            if ch is None:
                cy = Y_BLOCK + i * SZ_DATE
                o.append(
                    f'<rect x="{X_DATE-SZ_DATE*0.42:.2f}" y="{cy-SZ_DATE*0.42:.2f}" '
                    f'width="{SZ_DATE*0.84:.2f}" height="{SZ_DATE*0.84:.2f}" fill="none" '
                    f'stroke="#e4b9b9" stroke-width="0.3" stroke-dasharray="1 1.5"/>'
                )
        o.append(
            f'<circle cx="{SEAL_C[0]}" cy="{SEAL_C[1]}" r="{SEAL_R}" fill="none" '
            f'stroke="#e4b9b9" stroke-width="0.4" stroke-dasharray="2 2"/>'
        )

    # The crest stays out of the ink pass: a mon is a carved seal pressed in
    # one go, not a brushed stroke, so it should not fade at its thin points.
    cc = CREST_C_BORDERED if drawn_border else CREST_C
    if layer == "text":
        pass
    elif crest_kind == "bare":
        o.append(crest(*cc, CREST_R))
    elif crest_kind == "bottom":
        o.append(crest(*cc, CREST_R, ring_bottom=CFG.crest_ring))
    elif crest_kind == "full":
        o.append(crest(*cc, CREST_R, ring_bottom=CFG.crest_ring,
                       ring_top=CFG.art))

    if layer == "chrome":                       # ink layer supplies the text
        o.append("</svg>")
        return "\n".join(o)

    # printed columns
    o.append(vcol(list(heading), X_HEADING, Y_HEADING, SZ_HEADING, W_BOLD)[0])
    x_awardee, x_rank = right_columns(rank_column)
    if name:
        chars = list(name) + list(honorific or "")
        size = min(SZ_AWARDEE, AWARDEE_MAX_H / max(1, len(chars)))
        o.append(vcol(chars, x_awardee, Y_RANK, size, W_BOLD)[0])
    if rank:
        o.append(vcol(list(rank), (x_rank if name else X_RANK),
                      Y_RANK, SZ_RANK, W_BOLD)[0])
    o.append(vcol(list(verb), X_VERB, Y_VERB, SZ_VERB, W_BOLD)[0])
    # A printed date is set solid; a blank one keeps its slots spaced out so
    # the calligrapher has a grid to write into.
    o.append(vcol(date or DATE_SLOTS, X_DATE, Y_BLOCK, SZ_DATE, W_MED)[0])
    # Any of these may be empty in the config, in which case vcol draws
    # nothing and the column is simply absent.
    o.append(vcol(list(CFG.art), X_STYLE, Y_BLOCK, SZ_BLOCK, W_MED)[0])
    o.append(vcol(list(CFG.dojo), X_DOJO, Y_BLOCK, SZ_BLOCK, W_MED)[0])
    o.append(vcol(list(CFG.signer_title), X_TITLE, Y_BLOCK, SZ_TITLE, W_MED)[0])
    o.append(vcol(list(CFG.signer_name), X_SIGNER, Y_BLOCK, SZ_SIGNER, W_MED)[0])
    o.append(vcol(list(CFG.motto), X_MOTTO, Y_BLOCK, SZ_MOTTO, W_MED)[0])

    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ build ---
INK_DPI = 600.0          # resolution of the inked text raster
CSS_PX_PER_MM = 96.0 / 25.4


def _inked_text_image(base, verb, heading, kw, env, supersample=1):
    """Render the text layer alone, ink it, and return an <image> element.

    Rendered to the text's own bounding box rather than the page: a full A3 at
    600 dpi is mostly empty, and cropping is what makes supersampling
    affordable at all.

    `supersample` renders at N times the resolution and averages back down.
    Inkscape (via cairo) already antialiases analytically, so measurably this
    changes almost nothing — see DECISIONS.md — but the knob is here. Cairo
    refuses image surfaces wider than 32767 px, which caps the factor at 4 for
    an A3 text block.
    """
    from PIL import Image

    # Our own render, a few hundred megapixels at the higher factors. The
    # decompression-bomb guard is meant for untrusted input; it is not one here.
    Image.MAX_IMAGE_PIXELS = None

    tmp = base + "-textlayer"
    open(tmp + ".svg", "w").write(
        document(verb, heading, layer="text", **kw))

    # Drawing bounding box, in CSS px; the viewBox is 1 unit = 1 mm.
    q = subprocess.run(
        ["inkscape", tmp + ".svg", "--query-x", "--query-y",
         "--query-width", "--query-height"],
        check=True, capture_output=True, text=True, env=env)
    x, y, w, h = (float(v) / CSS_PX_PER_MM for v in q.stdout.split())

    subprocess.run(
        ["inkscape", tmp + ".svg", "--export-type=png", "--export-area-drawing",
         f"--export-dpi={INK_DPI * supersample:g}",
         "--export-background-opacity=0",
         "--export-filename=" + tmp + ".png"],
        check=True, capture_output=True, env=env)

    if supersample > 1:
        im = Image.open(tmp + ".png")
        target = (max(1, round(w * INK_DPI / 25.4)),
                  max(1, round(h * INK_DPI / 25.4)))
        im.resize(target, Image.LANCZOS).save(tmp + ".png")

    ink.ink_layer(tmp + ".png", tmp + ".png", INK_DPI)
    os.remove(tmp + ".svg")
    return (f'<image x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
            f'href="{os.path.basename(tmp)}.png" preserveAspectRatio="none"/>')


def _font_env():
    """Environment that makes the vendored font visible without installing it.

    Inkscape resolves families through fontconfig, so we hand it a config that
    includes the system one and adds ../fonts.  Nothing on the machine changes.
    """
    conf_dir = os.path.join(BUILD, ".fontconfig")
    os.makedirs(conf_dir, exist_ok=True)
    conf = os.path.join(conf_dir, "fonts.conf")
    with open(conf, "w") as fh:
        fh.write(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            "<fontconfig>\n"
            '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
            f"  <dir>{os.path.abspath(FONT_DIR)}</dir>\n"
            f"  <cachedir>{os.path.abspath(conf_dir)}/cache</cachedir>\n"
            "</fontconfig>\n")
    env = dict(os.environ)
    env["FONTCONFIG_FILE"] = os.path.abspath(conf)
    return env


def render(svg_path, out_base, formats, press=False, dpi=300,
           transparent=False, convert="gray"):
    """Export one intermediate SVG into `out_base` in the requested formats."""
    env = _font_env()
    written = []

    if "pdf" in formats:
        pdf = out_base + ".pdf"
        subprocess.run(
            ["inkscape", svg_path, "--export-type=pdf",
             "--export-filename=" + pdf],
            check=True, capture_output=True, env=env)
        written.append(pdf)
        if press:
            # The overlays are black text only, so K-only keeps them from
            # printing as a muddy four-colour black next to sumi ink; the full
            # artwork carries a sepia border and must stay in CMYK.
            if convert == "gray":
                suffix, strat, model = "-K", "/Gray", "/DeviceGray"
            else:
                suffix, strat, model = "-CMYK", "/CMYK", "/DeviceCMYK"
            subprocess.run(
                ["gs", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
                 "-dColorConversionStrategy=" + strat,
                 "-dProcessColorModel=" + model,
                 "-dPDFSETTINGS=/prepress", "-dEmbedAllFonts=true",
                 "-o", out_base + suffix + ".pdf", pdf],
                check=True, capture_output=True)
            written.append(out_base + suffix + ".pdf")

    if "png" in formats:
        png = out_base + ".png"
        cmd = ["inkscape", svg_path, "--export-type=png", f"--export-dpi={dpi}",
               "--export-filename=" + png]
        if transparent:
            cmd.append("--export-background-opacity=0")
        subprocess.run(cmd, check=True, capture_output=True, env=env)
        written.append(png)

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
CREAM = "#f7f1e3"

# The awards themselves come from the config ([[awards]]): slug, heading,
# formula, whether the body states a grade, and the drawn border's colour.
# The heading names the document, so several awards read apart at a glance;
# a grade column is for documents that state a specific grade as well —
# a dan certificate does, a teaching licence usually does not, since its
# heading has already named the award.  --rank overrides that either way.

VARIANTS = {
    # what you print onto bought Japanese 賞状用紙
    "overlay": dict(inked=True),
    # our own engraved border, for printing on cream stock
    "full": dict(drawn_border=True, inked=True),
    # the same with the paper tint printed too, for white stock — and the one
    # to look at on screen, since it shows the finished sheet
    "full-cream": dict(drawn_border=True, paper=CREAM, inked=True),
    # solid-black fallbacks: the graded text is a greyscale raster, and a home
    # laser halftones grey.  If the 12 mm columns come out mottled, print these.
    "overlay-flat": dict(),
    "full-flat": dict(drawn_border=True),
    # safe areas and the zones the calligrapher fills
    "proof": dict(guides=True),
}

DEFAULT_VARIANTS = ["overlay", "full-cream"]
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


def build_one(slug, heading, verb, variant, formats, press=False, dpi=300,
              inked=True, work=None, supersample=1, name=None, honorific="殿",
              rank=None, date=None, suffix="", rank_column=True,
              border_colour=SEPIA):
    kw = dict(VARIANTS[variant])
    kw["rank_column"] = rank_column or bool(rank)
    kw["border_colour"] = border_colour
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

    stem = f"{slug}-{variant}" + (f"-{suffix}" if suffix else "")
    svg_path = os.path.join(work, stem + ".svg")
    if use_ink:
        img = _inked_text_image(os.path.join(work, stem), verb, heading,
                                kw, _font_env(), supersample=supersample)
        svg = document(verb, heading, layer="chrome", **kw)
        svg = svg.replace("</svg>", img + "</svg>")
    else:
        svg = document(verb, heading, **kw)
    open(svg_path, "w").write(svg)

    return render(svg_path, os.path.join(BUILD, stem), formats,
                  press=press and variant != "proof", dpi=dpi,
                  transparent=not kw.get("guides") and not kw.get("paper"),
                  convert="cmyk" if kw.get("drawn_border") else "gray")


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


def main(argv=None):
    global CFG

    # --config has to be resolved before the parser is built, because the
    # awards it lists are what --awards will accept.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("-c", "--config", metavar="PATH")
    known, _ = pre.parse_known_args(argv)
    CFG = config_mod.load(known.config)
    slugs = CFG.slugs

    ap = argparse.ArgumentParser(
        prog="build_diploma.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Generate Japanese dan-grade and teaching-licence artwork.",
        epilog=(
            "By default this writes only what you would actually look at or\n"
            "print: the overlay for bought stock and the full-cream reference,\n"
            "for every award your config defines. Everything else is opt-in.\n"
            "\n"
            f"configuration: {os.path.relpath(CFG.source, os.getcwd())}\n"
            "  copy config/example.toml to dojo.toml and edit it, or use\n"
            "  --config to choose between several.\n"
            "\n"
            "examples:\n"
            "  build_diploma.py                          the sensible default\n"
            "  build_diploma.py --list                    show what that is\n"
            f"  build_diploma.py -a {slugs[0]} -v proof -f png    one proof sheet\n"
            "  build_diploma.py --press                   add -K / -CMYK for a printer\n"
            "  build_diploma.py --all --press             everything, for an archive\n"))
    ap.add_argument("-c", "--config", metavar="PATH",
                    help="certificate configuration to use (default: dojo.toml "
                         "in the repository root if it exists, otherwise "
                         "config/example.toml)")
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
    ap.add_argument("--press", action="store_true",
                    help="also write press-ready colour conversions: -K "
                         "greyscale for the overlays, -CMYK for the artwork. "
                         "Wanted by a commercial printer, not by yours.")
    ap.add_argument("--no-ink", action="store_true",
                    help="skip the sumi grading and set solid black; the same "
                         "thing the -flat variants give you")
    ap.add_argument("--dpi", type=int, default=300, metavar="N",
                    help="resolution for PNG output (default: 300)")
    ap.add_argument("-n", "--name", metavar="KATAKANA",
                    help="print the recipient's name in its own column instead "
                         "of leaving it for the calligrapher, e.g. "
                         "'ヤン・ヤンセン'. Shrinks to fit a long name. "
                         + _sample_help(CFG.sample_name))
    ap.add_argument("-r", "--rank", metavar="GRADE",
                    help="print the grade instead of leaving it for the "
                         "calligrapher. A number or romaji becomes kanji "
                         "(2 or nidan -> 二段, 1 -> 初段, up to 10); anything "
                         "else is printed as given, so the licences can use "
                         "this too: --rank 師範. "
                         + _sample_help(CFG.sample_rank))
    ap.add_argument("-d", "--date", metavar="YYYY-MM-DD",
                    help="print the award date in kanji instead of leaving it "
                         "for the calligrapher; 'today' also works. "
                         "西暦二〇二六年九月五日. "
                         + _sample_help(CFG.sample_date))
    ap.add_argument("--honorific", default=CFG.honorific, metavar="TEXT",
                    help="appended to the printed name (default: "
                         f"{CFG.honorific or 'none'}, from the config); "
                         "pass '' to leave it off")
    ap.add_argument("--suffix", metavar="TEXT",
                    help="tag appended to output filenames; defaults to the "
                         "name itself when --name is given, so one recipient's "
                         "files never overwrite another's"
                         + (f" (config: {CFG.sample_suffix})"
                            if CFG.sample_suffix else ""))
    ap.add_argument("--supersample", type=int, default=1, metavar="N",
                    help="render the sumi text layer at N times resolution and "
                         "average down (1-4, default: 1). Inkscape already "
                         "antialiases analytically, so this measurably changes "
                         "very little; 4 costs ~2 GB and about a minute.")
    ap.add_argument("--all", action="store_true",
                    help="shorthand for --awards all --variants all")
    ap.add_argument("--clean", action="store_true",
                    help="empty the build directory first")
    ap.add_argument("--list", action="store_true",
                    help="list the files that would be written, then stop")
    args = ap.parse_args(argv)

    if args.all:
        args.awards, args.variants = "all", "all"
    awards = _csv(args.awards, slugs, "award")
    variants = _csv(args.variants, list(VARIANTS), "variant")
    formats = _csv(args.formats, ["pdf", "png", "svg"], "format")
    if not 1 <= args.supersample <= 4:
        raise SystemExit(
            "--supersample must be between 1 and 4. Cairo, which Inkscape "
            "renders through, refuses image surfaces wider than 32767 px, and "
            "the A3 text block is 6622 px wide at 600 dpi — so 5x and beyond "
            "abort in the renderer, whatever the machine has.")

    # A flag left off falls back to the config's [sample]; a flag given as ''
    # clears that fallback for this run and leaves the slot blank again.
    name = _fallback(args.name, CFG.sample_name)
    raw_rank = _fallback(args.rank, CFG.sample_rank)
    raw_date = _fallback(args.date, CFG.sample_date)
    # A sample grade belongs only on the documents that state one. Printing it
    # on a licence would put 五段 on a sheet whose heading has already named
    # the award -- so the sample is gated on grade_column, while an explicit
    # --rank still goes on whatever you asked for (--rank 師範).
    sample_rank = args.rank is None and bool(raw_rank)

    rank = rank_kanji(raw_rank) if raw_rank else None
    date = date_column(raw_date) if raw_date else None
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
    tail = f"-{suffix}" if suffix else ""

    if args.list:
        for slug in awards:
            for v in variants:
                for ext in formats:
                    print(f"{slug}-{v}{tail}.{ext}")
                    if args.press and ext == "pdf" and v != "proof":
                        tag = "-CMYK" if "full" in v else "-K"
                        print(f"{slug}-{v}{tail}{tag}.pdf")
        return

    if args.clean and os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD, exist_ok=True)
    work = os.path.join(BUILD, ".work")
    os.makedirs(work, exist_ok=True)

    total = 0
    for slug in awards:
        aw = CFG.award(slug)
        heading, verb = aw.heading, aw.formula
        rank_column, border_colour = aw.grade_column, aw.colour
        for variant in variants:
            written = build_one(slug, heading, verb, variant, formats,
                                press=args.press, dpi=args.dpi,
                                inked=not args.no_ink, work=work,
                                supersample=args.supersample,
                                name=name, honorific=args.honorific,
                                rank=None if sample_rank and not rank_column
                                     else rank,
                                date=date, suffix=suffix,
                                rank_column=rank_column,
                                border_colour=border_colour)
            for w in written:
                print("wrote", os.path.relpath(w, os.path.dirname(BUILD)))
            total += len(written)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(os.path.join(BUILD, ".fontconfig"), ignore_errors=True)
    print(f"\n{total} file(s) in {os.path.relpath(BUILD, os.path.dirname(BUILD))}/")


if __name__ == "__main__":
    main()
