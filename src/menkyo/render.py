"""
Drawing the certificate: document()'s SVG as a PDF and as PNGs.

document() stays the one description of the sheet.  This module turns it
into pages, with nothing but Python packages:

    fonts     the two font files in fonts/, opened by path and checked before
              anything is drawn.  No font is ever looked up by its family
              name, so nothing installed on the machine is read.
    outlines  every <text> becomes the outlines of its glyphs, read by
              fontTools.  One glyph per character at its advance width: no
              kerning, ligatures or vertical forms, and document() needs none,
              since it sets one character per <text> and turns ー itself.
    pdf       our own writer for the small part of SVG that document() uses,
              straight to PDF operators.  Anything outside that part is
              refused with an error, never skipped: a layout change that needs
              more fails loudly instead of printing wrongly.
    raster    pdfium (pypdfium2) draws that PDF, for the PNG and for the
              600 dpi text layer that ink.py grades.

The PDF has no fonts.  Its text is filled paths, so it cannot be searched or
copied; these are print files.  A neutral colour is written as DeviceGray,
so the overlays carry no colour at all, and the inked text is a DeviceGray
image with a DeviceGray soft mask.  No dates, no IDs: the same input gives
the same bytes.
"""

import math
import os
import re
import xml.etree.ElementTree as ET
import zlib

from . import paths, png

PT_PER_MM = 72.0 / 25.4
SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

# A raster is drawn a band of rows at a time, each about this many bytes,
# and written out as it comes: a 300 dpi page is 17 MB in grey and 70 MB in
# RGBA, and neither is ever held whole.
BAND_BYTES = 2 ** 18


# ------------------------------------------------------------------ fonts ---
# font-family as document() writes it -> the file in fonts/, and what it is.
# The crest's family keeps the name the sheet has always asked for; the file
# is the Japanese subset of that same design (Noto Serif JP SemiBold,
# noto-cjk Serif2.003), so the ring reads as it did.
FONTS = {
    "Yuji Boku": ("YujiBoku-Regular.ttf", "Yuji Boku, the body face"),
    "Noto Serif CJK JP SemiBold": ("NotoSerifJP-SemiBold.otf",
                                   "Noto Serif JP SemiBold, the crest face"),
}
BODY, CREST = "Yuji Boku", "Noto Serif CJK JP SemiBold"
FONT_DIR = paths.resource("fonts")


class Face:
    """One font file: checked when opened, glyphs read on demand.

    A missing, unreadable or truncated file ends the run naming the file.
    fontTools reads lazily, so a file cut short would otherwise fail only at
    the first glyph past the cut; every table's extent is checked against the
    file's size instead, up front.
    """

    def __init__(self, family):
        from fontTools.ttLib import TTFont
        file, self.what = FONTS[family]
        self.path = os.path.join(FONT_DIR, file)
        self.family = family
        if not os.path.isfile(self.path):
            raise SystemExit(
                f"font file not found: {self.path} ({self.what}). It ships "
                f"with menkyo; reinstall the package.")
        try:
            size = os.path.getsize(self.path)
            self.font = TTFont(self.path, lazy=True)
            for tag, entry in self.font.reader.tables.items():
                if entry.offset + entry.length > size:
                    raise ValueError(f"table {tag!r} runs past the end of the file")
            self.cmap = self.font.getBestCmap()
            self.hmtx = self.font["hmtx"]
            self.upem = self.font["head"].unitsPerEm
            self.glyphs = self.font.getGlyphSet()
        except Exception as e:
            raise SystemExit(
                f"font file {self.path} ({self.what}) is unreadable or "
                f"corrupt: {type(e).__name__}: {e}. It ships with menkyo; "
                f"reinstall the package.")

    def has(self, ch):
        return ord(ch) in self.cmap

    def glyph(self, ch):
        """(glyph name, advance width in font units) for one character."""
        name = self.cmap.get(ord(ch))
        if name is None:
            # main() checks every string before drawing; this is the backstop.
            raise SystemExit(missing_glyph(ch, None, self))
        return name, self.hmtx[name][0]

    def draw(self, name, pen):
        try:
            self.glyphs[name].draw(pen)
        except Exception as e:
            raise SystemExit(
                f"font file {self.path} ({self.what}) is unreadable or "
                f"corrupt: glyph {name}: {type(e).__name__}: {e}")


_FACES = {}


def face(family):
    """The Face for a font-family document() writes; opened once a process."""
    if family not in FONTS:
        raise SystemExit(f"the PDF writer has no font for font-family {family!r}")
    if family not in _FACES:
        _FACES[family] = Face(family)
    return _FACES[family]


def open_fonts():
    """Open and check both fonts now, so a bad file stops the run before
    anything is written."""
    return [face(family) for family in FONTS]


def missing_glyph(ch, source, f):
    """The message for a character `f` cannot draw.  `source` says where the
    character came from: a flag, or a key in the configuration."""
    where = f" in {source}" if source else ""
    # A tab or a newline is printed escaped, so the message stays one line.
    shown = ch if ch.isprintable() else repr(ch)
    return (f"the character {shown} (U+{ord(ch):04X}){where} is not in "
            f"{f.what.split(',')[0]}, the font it would be printed in, so it "
            f"cannot be printed. Replace it with a character the font has, "
            f"such as a common variant of it.")


# --------------------------------------------------------------- matrices ---
def _mul(m, n):
    """The matrix that applies n first, then m (PDF order a b c d e f)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_TRANSFORM = re.compile(r"\s*(\w+)\s*\(([^)]*)\)\s*,?")


def parse_transform(s):
    m, pos = IDENTITY, 0
    for t in _TRANSFORM.finditer(s):
        if t.start() != pos:
            break
        pos = t.end()
        op = t.group(1)
        v = [float(x) for x in re.split(r"[\s,]+", t.group(2).strip()) if x]
        if op == "matrix" and len(v) == 6:
            n = tuple(v)
        elif op == "translate" and len(v) in (1, 2):
            n = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) == 2 else 0.0)
        elif op == "scale" and len(v) in (1, 2):
            n = (v[0], 0.0, 0.0, v[-1], 0.0, 0.0)
        elif op == "rotate" and len(v) in (1, 3):
            r = math.radians(v[0])
            n = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0.0, 0.0)
            if len(v) == 3:
                n = _mul((1.0, 0.0, 0.0, 1.0, v[1], v[2]),
                         _mul(n, (1.0, 0.0, 0.0, 1.0, -v[1], -v[2])))
        else:
            raise SystemExit(f"the PDF writer does not handle the transform "
                             f"{t.group(0).strip()!r}")
        m = _mul(m, n)
    if s[pos:].strip():
        raise SystemExit(f"the PDF writer does not handle the transform {s!r}")
    return m


# ------------------------------------------------------------- formatting ---
def _f(v):
    """A coordinate: four decimals are a tenth of a micrometre on the page."""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _g(v):
    """A matrix entry, to ten places: a glyph's scale is size / 1000, and
    rounding 11.5 / 1000 to three places makes the column 4 % too small.
    Fixed point, since PDF has no exponents: cos 90° is 6e-17, not 0."""
    s = f"{v:.10f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# -------------------------------------------------------------- path data ---
_PATH_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}


def path_ops(d):
    """SVG path data as PDF path operators.

    Takes M L H V C S Q T Z, absolute and relative; quadratics become
    cubics.  The arc (A) and anything else is refused.
    """
    toks = _PATH_TOKEN.findall(d)
    if "".join(toks) != re.sub(r"[\s,]", "", d):
        raise SystemExit(f"the PDF writer cannot read the path data {d[:60]!r}")
    ops, i, cmd = [], 0, None
    cx = cy = sx = sy = 0.0
    last_c = last_q = None

    def nums(n):
        nonlocal i
        part = toks[i:i + n]
        if len(part) < n or any(t.isalpha() for t in part):
            raise SystemExit(f"the PDF writer cannot read the path data {d[:60]!r}")
        i += n
        return [float(t) for t in part]

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd.upper() not in _ARGS:
                kind = " (an arc)" if cmd in "Aa" else ""
                raise SystemExit(f"the PDF writer does not handle the path "
                                 f"command {cmd}{kind}")
            if cmd in "Zz":
                ops.append("h")
                cx, cy = sx, sy
                last_c = last_q = None
                continue
        elif cmd is None or cmd in "Zz":
            raise SystemExit(f"the PDF writer cannot read the path data {d[:60]!r}")
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == "M":
            x, y = nums(2)
            cx, cy = sx, sy = x + ox, y + oy
            ops.append(f"{_f(cx)} {_f(cy)} m")
            cmd = "l" if rel else "L"           # pairs after a moveto draw lines
            last_c = last_q = None
        elif C in "LHV":
            if C == "L":
                x, y = nums(2)
                cx, cy = x + ox, y + oy
            elif C == "H":
                cx = nums(1)[0] + ox
            else:
                cy = nums(1)[0] + oy
            ops.append(f"{_f(cx)} {_f(cy)} l")
            last_c = last_q = None
        elif C in "CS":
            if C == "C":
                x1, y1, x2, y2, x, y = nums(6)
                x1, y1 = x1 + ox, y1 + oy
            else:
                x2, y2, x, y = nums(4)
                x1, y1 = (2 * cx - last_c[0], 2 * cy - last_c[1]) if last_c else (cx, cy)
            x2, y2, x, y = x2 + ox, y2 + oy, x + ox, y + oy
            ops.append(f"{_f(x1)} {_f(y1)} {_f(x2)} {_f(y2)} {_f(x)} {_f(y)} c")
            cx, cy, last_c, last_q = x, y, (x2, y2), None
        else:                                   # Q, T
            if C == "Q":
                qx, qy, x, y = nums(4)
                qx, qy = qx + ox, qy + oy
            else:
                x, y = nums(2)
                qx, qy = (2 * cx - last_q[0], 2 * cy - last_q[1]) if last_q else (cx, cy)
            x, y = x + ox, y + oy
            c1 = (cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy))
            c2 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
            ops.append(f"{_f(c1[0])} {_f(c1[1])} {_f(c2[0])} {_f(c2[1])} {_f(x)} {_f(y)} c")
            cx, cy, last_q, last_c = x, y, (qx, qy), None
    return ops


# Four cubic quarter-arcs make a circle, as every PDF writer does it.
KAPPA = 0.5522847498307936


def _circle_ops(cx, cy, r):
    k = KAPPA * r
    return [f"{_f(cx + r)} {_f(cy)} m",
            f"{_f(cx + r)} {_f(cy + k)} {_f(cx + k)} {_f(cy + r)} {_f(cx)} {_f(cy + r)} c",
            f"{_f(cx - k)} {_f(cy + r)} {_f(cx - r)} {_f(cy + k)} {_f(cx - r)} {_f(cy)} c",
            f"{_f(cx - r)} {_f(cy - k)} {_f(cx - k)} {_f(cy - r)} {_f(cx)} {_f(cy - r)} c",
            f"{_f(cx + k)} {_f(cy - r)} {_f(cx + r)} {_f(cy - k)} {_f(cx + r)} {_f(cy)} c",
            "h"]


def _glyph_pen():
    from fontTools.pens.basePen import BasePen

    class PdfPen(BasePen):
        """A glyph's outline as PDF path operators, in font units.  BasePen
        turns TrueType's quadratics into cubics on the way."""

        def __init__(self, glyphset):
            super().__init__(glyphset)
            self.ops = []

        def _moveTo(self, p):
            self.ops.append(f"{_f(p[0])} {_f(p[1])} m")

        def _lineTo(self, p):
            self.ops.append(f"{_f(p[0])} {_f(p[1])} l")

        def _curveToOne(self, p1, p2, p3):
            self.ops.append(f"{_f(p1[0])} {_f(p1[1])} {_f(p2[0])} {_f(p2[1])} "
                            f"{_f(p3[0])} {_f(p3[1])} c")

        def _closePath(self):
            self.ops.append("h")

    return PdfPen


# ------------------------------------------------------------ SVG -> PDF ----
# What the writer takes, element by element.  Anything else is refused.
_PAINT = {"fill", "stroke", "stroke-width", "stroke-dasharray", "fill-rule"}
ALLOWED = {
    "svg": {"width", "height", "viewBox"},
    "g": {"transform"},
    "rect": {"x", "y", "width", "height", "transform"} | _PAINT,
    "circle": {"cx", "cy", "r", "transform"} | _PAINT,
    "path": {"d", "transform"} | _PAINT,
    # font-weight picks nothing: each family is one file, at one weight.
    "text": {"x", "y", "font-family", "font-weight", "font-size", "fill",
             "text-anchor", "transform"},
    "image": {"x", "y", "width", "height", XLINK_HREF, "preserveAspectRatio"},
}
_ANCHOR = {"start": 0.0, "middle": 0.5, "end": 1.0}


def _colour(c, where):
    """'#rgb' or '#rrggbb' -> (PDF operands, is grey), or None for 'none'."""
    if c == "none":
        return None
    if re.fullmatch(r"#[0-9a-fA-F]{3}", c):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        raise SystemExit(f"the PDF writer does not handle the colour {c!r} on {where}")
    r, g, b = (int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    if r == g == b:
        return _f(r), True
    return f"{_f(r)} {_f(g)} {_f(b)}", False


def _mm(value, where):
    m = re.fullmatch(r"([\d.]+)mm", value or "")
    if not m:
        raise SystemExit(f"the PDF writer needs the page size in mm on {where}, "
                         f"not {value!r}")
    return float(m.group(1))


class Pdf:
    """A one-page PDF, as bytes, and what the raster step needs to know."""

    def __init__(self, data, size_pt, coloured):
        self.data, self.size_pt, self.coloured = data, size_pt, coloured


class _Writer:
    """Walks document()'s SVG and collects the page's content operators.

    `ink`, when given, paints every fill and stroke in that colour: the text
    layer is drawn in black, for its coverage.  The outline box of all text
    drawn is kept, in the SVG's user units: the exact bounds of the glyphs'
    curves, not of their control points.
    """

    def __init__(self, base_dir, ink=None):
        self.base_dir, self.ink = base_dir, ink
        self.ops, self.images, self.objs = [], [], []
        self.coloured = False
        self.bbox = None
        self.pen = _glyph_pen()

    def obj(self, body):
        self.objs.append(body)
        return len(self.objs)

    def stream(self, head, data, deflated=False):
        if not deflated:
            data = zlib.compress(data, 6)
        return self.obj(f"<< {head} /Filter /FlateDecode /Length {len(data)} >>\n"
                        f"stream\n".encode() + data + b"\nendstream")

    # -- the tree ------------------------------------------------------------
    def walk(self, el, ctm):
        tag = el.tag[len(SVG_NS):] if el.tag.startswith(SVG_NS) else el.tag
        if tag not in ALLOWED:
            raise SystemExit(f"the PDF writer does not handle the element <{tag}>")
        bad = sorted(set(el.attrib) - ALLOWED[tag])
        if bad:
            name = bad[0].replace("{http://www.w3.org/1999/xlink}", "xlink:")
            raise SystemExit(f"the PDF writer does not handle the attribute "
                             f"{name}=\"{el.get(bad[0])[:40]}\" on <{tag}>")
        if (el.text or "").strip() and tag != "text":
            raise SystemExit(f"the PDF writer does not handle text inside <{tag}>")
        if tag == "text" and len(el):
            raise SystemExit("the PDF writer does not handle elements inside <text>")
        tr = el.get("transform")
        if tr:
            m = parse_transform(tr)
            ctm = _mul(ctm, m)
            self.ops += ["q", " ".join(_g(v) for v in m) + " cm"]
        {"svg": self._children, "g": self._children, "rect": self._rect,
         "circle": self._circle, "path": self._path, "text": self._text,
         "image": self._image}[tag](el, ctm)
        if tr:
            self.ops.append("Q")

    def _children(self, el, ctm):
        for child in el:
            self.walk(child, ctm)
            if (child.tail or "").strip():
                raise SystemExit("the PDF writer does not handle text outside <text>")

    def _paint(self, el, shape):
        where = f"<{el.tag[len(SVG_NS):]}>"
        fill = self.ink if self.ink and el.get("fill") != "none" else el.get("fill", "#000000")
        stroke = el.get("stroke", "none")
        if self.ink and stroke != "none":
            stroke = self.ink
        fc, sc = _colour(fill, where), _colour(stroke, where)
        pre = []
        if fc:
            pre.append(f"{fc[0]} {'g' if fc[1] else 'rg'}")
            self.coloured |= not fc[1]
        if sc:
            pre.append(f"{sc[0]} {'G' if sc[1] else 'RG'}")
            self.coloured |= not sc[1]
            pre.append(f"{_f(float(el.get('stroke-width', '1')))} w")
            dash = el.get("stroke-dasharray", "none")
            pre.append("[] 0 d" if dash == "none" else
                       "[" + " ".join(_f(float(v)) for v in
                                      re.split(r"[\s,]+", dash.strip())) + "] 0 d")
        rule = el.get("fill-rule", "nonzero")
        if rule not in ("nonzero", "evenodd"):
            raise SystemExit(f"the PDF writer does not handle fill-rule={rule!r}")
        op = ("B" if fc and sc else "f" if fc else "S" if sc else "n")
        if fc and rule == "evenodd":
            op += "*"
        self.ops += pre + shape + [op]

    def _rect(self, el, ctm):
        self._paint(el, [f"{_f(float(el.get('x', 0)))} {_f(float(el.get('y', 0)))} "
                         f"{_f(float(el.get('width')))} {_f(float(el.get('height')))} re"])

    def _circle(self, el, ctm):
        self._paint(el, _circle_ops(float(el.get("cx", 0)), float(el.get("cy", 0)),
                                    float(el.get("r"))))

    def _path(self, el, ctm):
        self._paint(el, path_ops(el.get("d", "")))

    def _text(self, el, ctm):
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.transformPen import TransformPen
        f = face(el.get("font-family", BODY))
        size = float(el.get("font-size"))
        anchor = el.get("text-anchor", "start")
        if anchor not in _ANCHOR:
            raise SystemExit(f"the PDF writer does not handle text-anchor={anchor!r}")
        fill = self.ink or el.get("fill", "#000000")
        fc = _colour(fill, "<text>")
        if fc is None:
            return
        self.coloured |= not fc[1]
        glyphs = [f.glyph(ch) for ch in (el.text or "")]
        s = size / f.upem
        x = float(el.get("x", 0)) - _ANCHOR[anchor] * sum(w for _, w in glyphs) * s
        y = float(el.get("y", 0))
        self.ops.append(f"{fc[0]} {'g' if fc[1] else 'rg'}")
        for name, advance in glyphs:
            gm = (s, 0.0, 0.0, -s, x, y)            # font units, y up -> user units
            pen = self.pen(f.glyphs)
            f.draw(name, pen)
            if pen.ops:
                self.ops += ["q", " ".join(_g(v) for v in gm) + " cm", *pen.ops, "f", "Q"]
                bp = BoundsPen(f.glyphs)
                f.draw(name, TransformPen(bp, _mul(ctm, gm)))
                if bp.bounds:
                    b = bp.bounds
                    self.bbox = b if self.bbox is None else (
                        min(self.bbox[0], b[0]), min(self.bbox[1], b[1]),
                        max(self.bbox[2], b[2]), max(self.bbox[3], b[3]))
            x += advance * s

    def _image(self, el, ctm):
        if el.get("preserveAspectRatio") != "none":
            raise SystemExit("the PDF writer needs preserveAspectRatio=\"none\" on <image>")
        href = el.get(XLINK_HREF)
        if not href or "/" in href or ":" in href:
            raise SystemExit(f"the PDF writer takes an <image> beside the SVG only, "
                             f"not {href!r}")
        (w, h), grey, alpha = _grey_and_alpha(os.path.join(self.base_dir, href))
        head = (f"/Type /XObject /Subtype /Image /Width {w} /Height {h} "
                f"/ColorSpace /DeviceGray /BitsPerComponent 8")
        smask = self.stream(head, alpha, deflated=True)
        img = self.stream(head + f" /SMask {smask} 0 R", grey, deflated=True)
        name = f"Im{len(self.images)}"
        self.images.append((name, img))
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        iw, ih = float(el.get("width")), float(el.get("height"))
        self.ops.append(f"q {_f(iw)} 0 0 {_f(-ih)} {_f(x)} {_f(y + ih)} cm /{name} Do Q")


def _grey_and_alpha(path):
    """An LA or grey RGBA PNG as two deflated DeviceGray planes: (size, grey,
    alpha).  Read a band at a time when png can stream it, else whole."""
    def deflate(rows, bpp):
        zg, za = zlib.compressobj(6), zlib.compressobj(6)
        grey, alpha = [], []
        for r in rows:
            g = r[0::bpp]
            if bpp == 4 and not (g == r[1::4] == r[2::4]):
                raise SystemExit(f"the PDF writer takes a grey image only ({path})")
            grey.append(zg.compress(g))
            alpha.append(za.compress(r[bpp - 1::bpp]))
        return b"".join(grey) + zg.flush(), b"".join(alpha) + za.flush()

    try:
        w, h, mode = png.header(path)
        rows = (r for band in png.bands(path) for r in band)
        return (w, h), *deflate(rows, 2 if mode == "LA" else 4)
    except png.NotStreamable:
        from PIL import Image
        with Image.open(path) as im:
            if im.mode not in ("RGBA", "LA"):
                raise SystemExit(f"the PDF writer needs an RGBA or LA image, "
                                 f"not {im.mode} ({path})")
            im.load()
            data, bpp, (w, h) = im.tobytes(), len(im.mode), im.size
        rows = (data[i:i + w * bpp] for i in range(0, len(data), w * bpp))
        return (w, h), *deflate(rows, bpp)


def svg_to_pdf(svg, base_dir=".", area=None, ink=None):
    """One page of PDF from `svg`, document()'s output, as a Pdf.

    `area` is a box (x, y, w, h in user units) to make the page instead of
    the whole sheet.  With area="text", the box is the outline box of the
    text drawn: the text layer, cropped to its own extent.  `ink` paints
    everything in one colour.  Returns the Pdf, and the outline box.
    """
    root = ET.fromstring(svg)
    if root.tag != SVG_NS + "svg":
        raise SystemExit("the PDF writer needs an <svg> root")
    vb = [float(v) for v in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if v]
    if len(vb) != 4:
        raise SystemExit("the PDF writer needs a viewBox on the <svg> root")
    width, height = _mm(root.get("width"), "<svg>"), _mm(root.get("height"), "<svg>")
    if abs(width / vb[2] - height / vb[3]) > 1e-9:
        raise SystemExit("the PDF writer needs the viewBox to keep the page's proportions")

    w = _Writer(base_dir, ink)
    w.walk(root, IDENTITY)
    if area == "text":
        if w.bbox is None:
            return None, None
        x0, y0, x1, y1 = w.bbox
        area = (x0, y0, x1 - x0, y1 - y0)
    box = area or (vb[0], vb[1], vb[2], vb[3])
    k = PT_PER_MM * width / vb[2]               # user units -> points
    W, H = box[2] * k, box[3] * k
    # User space is y-down from the box's corner; PDF's is y-up from the page's.
    ops = ["q", f"{_g(k)} 0 0 {_g(-k)} {_g(-box[0] * k)} {_g((box[1] + box[3]) * k)} cm",
           "4 M"] + w.ops + ["Q"]
    content = w.stream("", "\n".join(ops).encode())
    xobj = " ".join(f"/{n} {o} 0 R" for n, o in w.images)
    res = f"<< /XObject << {xobj} >> >>" if w.images else "<< >>"
    pages = len(w.objs) + 2
    page = w.obj(f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_f(W)} {_f(H)}] "
                 f"/Resources {res} /Contents {content} 0 R >>")
    w.obj(f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>")
    catalog = w.obj(f"<< /Type /Catalog /Pages {pages} 0 R >>")
    info = w.obj("<< /Producer (menkyo) >>")

    out = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    at, offsets = len(out[0]), []
    for i, body in enumerate(w.objs, 1):
        chunk = (f"{i} 0 obj\n".encode()
                 + (body if isinstance(body, bytes) else body.encode()) + b"\nendobj\n")
        offsets.append(at)
        out.append(chunk)
        at += len(chunk)
    out.append(f"xref\n0 {len(w.objs) + 1}\n0000000000 65535 f \n".encode())
    out += [f"{o:010d} 00000 n \n".encode() for o in offsets]
    out.append(f"trailer\n<< /Size {len(w.objs) + 1} /Root {catalog} 0 R "
               f"/Info {info} 0 R >>\nstartxref\n{at}\n%%EOF\n".encode())
    return Pdf(b"".join(out), (W, H), w.coloured), area


# ---------------------------------------------------------------- raster ----
def _bands(pdf, size, colour):
    """pdfium's drawing of the page at `size` pixels, a band of rows at a
    time: RGBA on transparency when `colour`, else grey on white.  Yields
    each band as a list of rows (bytes)."""
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    W, H = size
    if colour:
        fmt, bpp, fill = raw.FPDFBitmap_BGRA, 4, 0x00FFFFFF
        flags = raw.FPDF_REVERSE_BYTE_ORDER             # RGBA, not BGRA
    else:
        fmt, bpp, fill, flags = raw.FPDFBitmap_Gray, 1, 0xFFFFFFFF, 0
    doc = pdfium.PdfDocument(pdf.data)
    page = doc[0]
    rows = max(1, min(H, BAND_BYTES // (W * bpp)))
    bm = raw.FPDFBitmap_CreateEx(W, rows, fmt, None, 0)
    if not bm:
        raise MemoryError(f"pdfium could not make a {W} x {rows} bitmap")
    try:
        pw, ph = page.get_size()
        stride = raw.FPDFBitmap_GetStride(bm)
        for y0 in range(0, H, rows):
            n = min(rows, H - y0)
            raw.FPDFBitmap_FillRect(bm, 0, 0, W, rows, fill)
            raw.FPDF_RenderPageBitmapWithMatrix(
                bm, page.raw, raw.FS_MATRIX(W / pw, 0, 0, H / ph, 0, -y0),
                raw.FS_RECTF(0, 0, W, n), flags)
            buf = ctypes.string_at(raw.FPDFBitmap_GetBuffer(bm), stride * n)
            yield [buf[i * stride:i * stride + W * bpp] for i in range(n)]
    finally:
        raw.FPDFBitmap_Destroy(bm)
        page.close()
        doc.close()


def _grey_alpha(ink):
    """Grey-on-white -> the alpha of `ink` over white that gives that grey.
    Over white it is the same pixel; the PNG keeps its transparency."""
    return bytes(min(255, round((255 - v) * 255 / (255 - ink))) for v in range(256))


def _la(bands, width, ink, lut):
    """Grey bands as LA rows: `ink` under the alpha `lut` makes of the grey."""
    for rows in bands:
        out = []
        for r in rows:
            b = bytearray(2 * width)
            b[0::2] = bytes([ink]) * width
            b[1::2] = r.translate(lut)
            out.append(b)
        yield out


def page_png(pdf, path, dpi, ink=0x11):
    """The page as a PNG at `dpi`, transparent where nothing is drawn.

    A page with colour on it (the proof) is drawn in RGBA.  One without is
    drawn in grey, a quarter of the memory, and written as LA: `ink`, the
    grey everything on such a page is drawn in, under the alpha that gives
    the grey pdfium drew.
    """
    W, H = (round(v * dpi / 72.0) for v in pdf.size_pt)
    if pdf.coloured:
        return png.write(path, (W, H), "RGBA", _bands(pdf, (W, H), True), dpi)
    return png.write(path, (W, H), "LA",
                     _la(_bands(pdf, (W, H), False), W, ink, _grey_alpha(ink)), dpi)


def text_layer(svg, path, dpi, ink=0x11):
    """The text alone, cropped to its outlines, as an LA PNG at `dpi`.

    The colour is `ink`; the alpha is the glyph coverage pdfium drew, which
    is what ink.ink_layer grades.  Returns the box (x, y, w, h) in the SVG's
    user units, or None when there is no text.  The pixel size is the box at
    `dpi`, rounded per side, and the box is mapped onto it exactly.
    """
    pdf, box = svg_to_pdf(svg, area="text", ink="#000000")
    if pdf is None:
        return None
    x, y, w, h = box
    size = (max(1, round(w * dpi / 25.4)), max(1, round(h * dpi / 25.4)))
    cover = bytes(255 - v for v in range(256))     # black on white -> coverage
    png.write(path, size, "LA", _la(_bands(pdf, size, False), size[0], ink, cover), dpi)
    return box
