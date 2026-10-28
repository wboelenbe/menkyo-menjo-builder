"""
norender: an Inkscape-free renderer for menkyo, as prototyped by the
no-inkscape spike (D-3). Not production code; see spike.md.

The route keeps build_diploma.document() as the single source of the drawing
and replaces only what Inkscape did with it:

1. outline_svg() turns every <text> into a <path> of the glyph's outline,
   read by fontTools from a font *file*: Yuji Boku (vendored) and the crest
   mincho. Fonts are never looked up by family name, so nothing installed on
   the machine is ever read (P-3).
2. svg_to_pdf() writes the SVG subset document() emits -- svg, g, rect,
   circle, path, image; transforms; fill, stroke, dashes, even-odd -- straight
   to PDF operators. A neutral colour (r = g = b) is written as DeviceGray, so
   the overlays come out grey (F-6), and the inked raster is a DeviceGray
   image with a DeviceGray soft mask. No dates, no IDs: same input, same bytes.
3. rasterise() hands that PDF to pdfium (pypdfium2), so the PNG and the
   600 dpi text layer are drawn from the very same paths as the PDF.

The runner-up swaps step 3 for resvg (resvg-py) on the outlined SVG.

Font files come from SPIKE_FONT_BODY / SPIKE_FONT_CREST, defaulting to the
package's Yuji Boku and $SPIKE_FONTS/NotoSerifJP-SemiBold.otf. SPIKE_MISSING
is "error" (default) or "fallback" (a character Yuji Boku lacks is drawn from
the crest mincho), for G-4.
"""

import html
import io
import math
import os
import re
import zlib
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

PT_PER_MM = 72.0 / 25.4
SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


# ------------------------------------------------------------------ fonts ---
class Face:
    """One font file, checked up front; glyph outlines and advances on demand.

    A missing, unreadable or truncated file stops the build with a message
    naming the file (G-6). Every table's extent is checked against the file
    size, because fontTools reads lazily and a truncated file would otherwise
    only fail on the first glyph that lives past the cut.
    """

    def __init__(self, path, role):
        from fontTools.ttLib import TTFont
        self.path, self.role = path, role
        if not os.path.isfile(path):
            raise SystemExit(f"font file not found: {path} ({role})")
        try:
            size = os.path.getsize(path)
            self.font = TTFont(path, lazy=True)
            for tag, entry in self.font.reader.tables.items():
                if entry.offset + entry.length > size:
                    raise ValueError(f"table {tag!r} runs past the end of the file")
            self.cmap = self.font.getBestCmap()
            self.hmtx = self.font["hmtx"]
            self.upem = self.font["head"].unitsPerEm
            self.glyphs = self.font.getGlyphSet()
            self.name = self.font["name"].getDebugName(4) or os.path.basename(path)
        except SystemExit:
            raise
        except Exception as e:
            raise SystemExit(
                f"font file {path} ({role}) is unreadable or corrupt: "
                f"{type(e).__name__}: {e}")
        self._cache = {}

    def has(self, ch):
        return ord(ch) in self.cmap

    def outline(self, ch):
        """(path data in font units, y up; advance width) for one character."""
        if ch not in self._cache:
            from fontTools.pens.svgPathPen import SVGPathPen
            gname = self.cmap[ord(ch)]
            pen = SVGPathPen(self.glyphs, ntos=_num)
            try:
                self.glyphs[gname].draw(pen)
            except Exception as e:
                raise SystemExit(
                    f"font file {self.path} ({self.role}) is unreadable or "
                    f"corrupt: glyph for {ch!r}: {type(e).__name__}: {e}")
            self._cache[ch] = (pen.getCommands(), self.hmtx[gname][0])
        return self._cache[ch]

    def bounds(self, ch, matrix):
        """Exact bounds of the glyph after `matrix` (font units -> user units)."""
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.transformPen import TransformPen
        bp = BoundsPen(self.glyphs)
        self.glyphs[self.cmap[ord(ch)]].draw(TransformPen(bp, matrix))
        return bp.bounds


def _num(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


_FACES = {}


def font_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    from menkyo import paths
    body = os.environ.get("SPIKE_FONT_BODY") or paths.resource("fonts", "YujiBoku-Regular.ttf")
    crest = os.environ.get("SPIKE_FONT_CREST") or os.path.join(
        os.environ.get("SPIKE_FONTS", os.path.join(here, "fonts")),
        "NotoSerifJP-SemiBold.otf")
    return {"Yuji Boku": (body, "body face, Yuji Boku"),
            "Noto Serif CJK JP SemiBold": (crest, "crest mincho")}


def face(family):
    """The Face for a font-family name document() writes; files, not lookups."""
    table = font_paths()
    if family not in table:
        raise SystemExit(f"no font file configured for font-family {family!r}")
    path, role = table[family]
    key = (family, path)
    if key not in _FACES:
        _FACES[key] = Face(path, role)
    return _FACES[key]


def check_fonts():
    """Open both faces now, so a bad file fails before anything is drawn."""
    for fam in font_paths():
        face(fam)


# --------------------------------------------------------------- matrices ---
def mul(m, n):
    """m after n: the matrix of applying n first, then m (PDF a b c d e f)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def parse_transform(s):
    m = (1, 0, 0, 1, 0, 0)
    for op, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if op == "matrix":
            t = tuple(v)
        elif op == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif op == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif op == "rotate":
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = mul((1, 0, 0, 1, v[1], v[2]), mul(t, (1, 0, 0, 1, -v[1], -v[2])))
        else:
            raise ValueError(f"unsupported transform {op}")
        m = mul(m, t)
    return m


# ---------------------------------------------------------- text -> paths ---
TEXT_RE = re.compile(r"<text ([^>]*)>([^<]*)</text>")
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')


class MissingGlyph(SystemExit):
    pass


def _resolve(ch, family):
    f = face(family)
    if f.has(ch):
        return f
    policy = os.environ.get("SPIKE_MISSING", "error")
    if policy == "fallback" and family != "Noto Serif CJK JP SemiBold":
        fb = face("Noto Serif CJK JP SemiBold")
        if fb.has(ch):
            return fb
    raise MissingGlyph(
        f"the character {ch} (U+{ord(ch):04X}) is not in {f.name} "
        f"({os.path.basename(f.path)}); it cannot be printed in this face")


def outline_svg(svg, glyph_log=None):
    """Replace each <text> with its outline. Returns (svg, bbox or None).

    bbox (x, y, w, h in user units, mm) is the union of the exact outline
    bounds; it is only computed for text with no transformed ancestor, which
    is all of document()'s text layer -- the input to the ink pass.
    """
    boxes = []

    def sub(m):
        a = dict(ATTR_RE.findall(m.group(1)))
        text = html.unescape(m.group(2))
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        size = float(a["font-size"])
        family = a.get("font-family", "Yuji Boku")
        outer = parse_transform(a.get("transform"))
        resolved = [(ch, _resolve(ch, family)) for ch in text]
        adv = sum(f.outline(ch)[1] * size / f.upem for ch, f in resolved)
        anchor = a.get("text-anchor", "start")
        pen_x = x - (adv / 2 if anchor == "middle" else adv if anchor == "end" else 0)
        out = []
        for ch, f in resolved:
            d, w = f.outline(ch)
            s = size / f.upem
            gm = mul(outer, (s, 0, 0, -s, pen_x, y))
            if glyph_log is not None:
                glyph_log.append(dict(ch=ch, family=family, face=f.name, x=x, y=y,
                                      size=size, transform=a.get("transform", "")))
            if d:
                boxes.append(f.bounds(ch, gm))
                out.append(
                    f'<path d="{d}" fill="{a.get("fill", "#000")}" '
                    f'transform="matrix({" ".join(f"{v:.9g}" for v in gm)})"/>')
            pen_x += w * s
        return "\n".join(out)

    out = TEXT_RE.sub(sub, svg)
    bbox = None
    boxes = [b for b in boxes if b]
    if boxes:
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
        bbox = (x0, y0, x1 - x0, y1 - y0)
    return out, bbox


# ------------------------------------------------------------- SVG -> PDF ---
NUM_RE = re.compile(r"[MmLlHhVvCcSsQqTtZzAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
KAPPA = 0.5522847498307936


def _f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _colour(c):
    """'#rrggbb' -> (operands, is_gray) or None for none."""
    if c is None or c == "none":
        return None
    named = {"black": "#000000", "white": "#ffffff"}
    c = named.get(c, c)
    if re.fullmatch(r"#[0-9a-fA-F]{3}", c):
        c = "#" + "".join(ch * 2 for ch in c[1:])
    r, g, b = (int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    if r == g == b:
        return f"{_f(r)}", True
    return f"{_f(r)} {_f(g)} {_f(b)}", False


def _path_ops(d):
    """SVG path data -> PDF path operators (absolute; quadratics to cubics)."""
    toks = NUM_RE.findall(d)
    ops, i, cmd = [], 0, None
    cx = cy = sx = sy = 0.0
    last_c2 = last_q = None

    def nums(n):
        nonlocal i
        v = [float(t) for t in toks[i:i + n]]
        i += n
        return v

    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                ops.append("h")
                cx, cy = sx, sy
                last_c2 = last_q = None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == "M":
            x, y = nums(2)
            cx, cy = sx, sy = x + ox, y + oy
            ops.append(f"{_f(cx)} {_f(cy)} m")
            cmd = "l" if rel else "L"          # implicit lineto after moveto
            last_c2 = last_q = None
        elif C == "L":
            x, y = nums(2)
            cx, cy = x + ox, y + oy
            ops.append(f"{_f(cx)} {_f(cy)} l")
            last_c2 = last_q = None
        elif C == "H":
            (x,) = nums(1)
            cx = x + ox
            ops.append(f"{_f(cx)} {_f(cy)} l")
            last_c2 = last_q = None
        elif C == "V":
            (y,) = nums(1)
            cy = y + oy
            ops.append(f"{_f(cx)} {_f(cy)} l")
            last_c2 = last_q = None
        elif C in "CS":
            if C == "C":
                x1, y1, x2, y2, x, y = nums(6)
                x1, y1 = x1 + ox, y1 + oy
            else:
                x2, y2, x, y = nums(4)
                x1, y1 = (2 * cx - last_c2[0], 2 * cy - last_c2[1]) if last_c2 else (cx, cy)
            x2, y2, x, y = x2 + ox, y2 + oy, x + ox, y + oy
            ops.append(f"{_f(x1)} {_f(y1)} {_f(x2)} {_f(y2)} {_f(x)} {_f(y)} c")
            cx, cy, last_c2, last_q = x, y, (x2, y2), None
        elif C in "QT":
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
            cx, cy, last_q, last_c2 = x, y, (qx, qy), None
        else:
            raise ValueError(f"unsupported path command {cmd!r}")
    return ops


def _circle_ops(cx, cy, r):
    k = KAPPA * r
    return [f"{_f(cx + r)} {_f(cy)} m",
            f"{_f(cx + r)} {_f(cy + k)} {_f(cx + k)} {_f(cy + r)} {_f(cx)} {_f(cy + r)} c",
            f"{_f(cx - k)} {_f(cy + r)} {_f(cx - r)} {_f(cy + k)} {_f(cx - r)} {_f(cy)} c",
            f"{_f(cx - r)} {_f(cy - k)} {_f(cx - k)} {_f(cy - r)} {_f(cx)} {_f(cy - r)} c",
            f"{_f(cx + k)} {_f(cy - r)} {_f(cx + r)} {_f(cy - k)} {_f(cx + r)} {_f(cy)} c",
            "h"]


def _up_predict(arr):
    """PNG 'Up' filter per row, for /Predictor 12: deflates far better."""
    a = arr.astype(np.int16)
    diff = np.empty_like(a)
    diff[0] = a[0]
    diff[1:] = a[1:] - a[:-1]
    rows = (diff % 256).astype(np.uint8)
    return np.concatenate([np.full((rows.shape[0], 1), 2, np.uint8), rows], axis=1).tobytes()


class _Pdf:
    def __init__(self):
        self.objs = []

    def add(self, body):
        self.objs.append(body)
        return len(self.objs)

    def stream(self, dict_extra, data, compress=True):
        if compress:
            data = zlib.compress(data, 6)
            dict_extra += " /Filter /FlateDecode"
        return self.add(f"<< {dict_extra} /Length {len(data)} >>\nstream\n".encode()
                        + data + b"\nendstream")

    def bytes(self, root, info):
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offs = []
        for i, body in enumerate(self.objs, 1):
            offs.append(out.tell())
            out.write(f"{i} 0 obj\n".encode())
            out.write(body if isinstance(body, bytes) else body.encode())
            out.write(b"\nendobj\n")
        x = out.tell()
        out.write(f"xref\n0 {len(self.objs) + 1}\n0000000000 65535 f \n".encode())
        for o in offs:
            out.write(f"{o:010d} 00000 n \n".encode())
        out.write(f"trailer\n<< /Size {len(self.objs) + 1} /Root {root} 0 R "
                  f"/Info {info} 0 R >>\nstartxref\n{x}\n%%EOF\n".encode())
        return out.getvalue()


def svg_to_pdf(svg, base_dir=".", area=None, fill_override=None):
    """One-page PDF from the SVG subset document() writes (text outlined).

    `area` (x, y, w, h in user units) crops the page to that box: the text
    layer's own bbox, as Inkscape's --export-area-drawing did. Otherwise the
    page is the root's viewBox. `fill_override` paints every fill in one
    colour (the text layer is rendered black for its coverage).
    """
    root = ET.fromstring(svg)
    vb = [float(v) for v in root.get("viewBox").split()]
    x0, y0, w, h = area or vb
    W, H = w * PT_PER_MM, h * PT_PER_MM
    pdf = _Pdf()
    images = []
    ops = ["q", f"{_f(PT_PER_MM)} 0 0 {_f(-PT_PER_MM)} {_f(-x0 * PT_PER_MM)} {_f((y0 + h) * PT_PER_MM)} cm",
           "4 M"]

    def paint(el, inh, shape_ops):
        fill = el.get("fill", inh.get("fill", "#000000"))
        stroke = el.get("stroke", inh.get("stroke", "none"))
        if fill_override and fill != "none":
            fill = fill_override
        fc, sc = _colour(fill), _colour(stroke)
        pre = []
        if fc:
            pre.append(f"{fc[0]} {'g' if fc[1] else 'rg'}")
        if sc:
            pre.append(f"{sc[0]} {'G' if sc[1] else 'RG'}")
            pre.append(f"{_f(float(el.get('stroke-width', inh.get('stroke-width', 1))))} w")
            dash = el.get("stroke-dasharray", "none")
            pre.append(f"[{' '.join(_f(float(v)) for v in re.split(r'[ ,]+', dash.strip()))}] 0 d"
                       if dash != "none" else "[] 0 d")
        eo = el.get("fill-rule", inh.get("fill-rule")) == "evenodd"
        op = ("B" if fc and sc else "f" if fc else "S" if sc else "n") + ("*" if eo and fc else "")
        ops.extend(pre + shape_ops + [op])

    def walk(el, inh):
        tag = el.tag.replace(SVG_NS, "")
        tr = el.get("transform")
        if tr:
            ops.append("q")
            ops.append(" ".join(_f(v) for v in parse_transform(tr)) + " cm")
        inh = dict(inh)
        for k in ("fill", "stroke", "stroke-width", "fill-rule"):
            if el.get(k) is not None and tag in ("g", "svg"):
                inh[k] = el.get(k)
        if tag in ("svg", "g"):
            for c in el:
                walk(c, inh)
        elif tag == "rect":
            rx, ry = float(el.get("x", 0)), float(el.get("y", 0))
            paint(el, inh, [f"{_f(rx)} {_f(ry)} {_f(float(el.get('width')))} {_f(float(el.get('height')))} re"])
        elif tag == "circle":
            paint(el, inh, _circle_ops(float(el.get("cx", 0)), float(el.get("cy", 0)), float(el.get("r"))))
        elif tag == "path":
            paint(el, inh, _path_ops(el.get("d", "")))
        elif tag == "image":
            href = el.get(XLINK_HREF) or el.get("href")
            im = Image.open(os.path.join(base_dir, href)).convert("RGBA")
            a = np.asarray(im)
            grey = np.asarray(im.convert("RGB").convert("L"))
            iw, ih = im.size
            parms = f"/DecodeParms << /Predictor 12 /Colors 1 /BitsPerComponent 8 /Columns {iw} >>"
            smask = pdf.stream(f"/Type /XObject /Subtype /Image /Width {iw} /Height {ih} "
                               f"/ColorSpace /DeviceGray /BitsPerComponent 8 {parms}",
                               _up_predict(a[..., 3]))
            img = pdf.stream(f"/Type /XObject /Subtype /Image /Width {iw} /Height {ih} "
                             f"/ColorSpace /DeviceGray /BitsPerComponent 8 /SMask {smask} 0 R {parms}",
                             _up_predict(grey))
            name = f"Im{len(images)}"
            images.append((name, img))
            ix, iy = float(el.get("x", 0)), float(el.get("y", 0))
            iw_, ih_ = float(el.get("width")), float(el.get("height"))
            ops.append(f"q {_f(iw_)} 0 0 {_f(-ih_)} {_f(ix)} {_f(iy + ih_)} cm /{name} Do Q")
        if tr:
            ops.append("Q")

    walk(root, {})
    ops.append("Q")
    content = pdf.stream("", "\n".join(ops).encode())
    xobj = " ".join(f"/{n} {o} 0 R" for n, o in images)
    res = f"<< /XObject << {xobj} >> >>" if images else "<< >>"
    pages = len(pdf.objs) + 2
    page = pdf.add(f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_f(W)} {_f(H)}] "
                   f"/Resources {res} /Contents {content} 0 R >>")
    assert pdf.add(f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>") == pages
    cat = pdf.add(f"<< /Type /Catalog /Pages {pages} 0 R >>")
    info = pdf.add("<< /Producer (menkyo no-inkscape spike) >>")
    return pdf.bytes(cat, info)


# --------------------------------------------------------------- raster -----
def rasterise(pdf_bytes, size, transparent, grey=False):
    """Render page 1 with pdfium to exactly `size` (w, h) pixels.

    Returns a PIL image: 'L' when grey (the coverage of black-on-white), else
    'RGBA' -- transparent background, or opaque white.
    """
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    doc = pdfium.PdfDocument(pdf_bytes)
    page = doc[0]
    pw, ph = page.get_size()
    W, H = size
    fmt = raw.FPDFBitmap_Gray if grey else raw.FPDFBitmap_BGRA
    bm = raw.FPDFBitmap_CreateEx(W, H, fmt, None, 0)
    if not bm:
        raise MemoryError(f"pdfium could not allocate a {W}x{H} bitmap")
    try:
        raw.FPDFBitmap_FillRect(bm, 0, 0, W, H, 0x00FFFFFF if transparent and not grey else 0xFFFFFFFF)
        m = raw.FS_MATRIX(W / pw, 0, 0, H / ph, 0, 0)
        clip = raw.FS_RECTF(0, 0, W, H)
        raw.FPDF_RenderPageBitmapWithMatrix(bm, page.raw, m, clip, 0)
        stride = raw.FPDFBitmap_GetStride(bm)
        buf = ctypes.cast(raw.FPDFBitmap_GetBuffer(bm), ctypes.POINTER(ctypes.c_ubyte * (stride * H))).contents
        # One copy, decoded straight from pdfium's BGRA (or grey) rows.
        im = Image.frombuffer("L" if grey else "RGBA", (W, H), buf, "raw",
                              "L" if grey else "BGRA", stride, 1).copy()
    finally:
        raw.FPDFBitmap_Destroy(bm)
        page.close()
        doc.close()
    return im


def rasterise_resvg(svg, size, transparent, base_dir=".", area=None):
    """The runner-up: resvg on the outlined SVG, no fonts loaded at all."""
    import resvg_py
    x, y, w, h = area or [float(v) for v in re.search(r'viewBox="([^"]*)"', svg).group(1).split()]
    svg = re.sub(r'viewBox="[^"]*"', f'viewBox="{x} {y} {w} {h}"', svg, count=1)
    # resvg-py 0.5 refuses an explicit pixel size on a root sized in mm
    # ("SVG has an invalid size"); unitless is fine, the pixel size is ours.
    svg = re.sub(r'width="[^"]*mm" height="[^"]*mm"', f'width="{w}" height="{h}"', svg, count=1)
    png = resvg_py.svg_to_bytes(svg_string=svg, width=size[0], height=size[1],
                                skip_system_fonts=True, resources_dir=os.path.abspath(base_dir),
                                background=None if transparent else "#ffffff")
    im = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
    if im.size != tuple(size):
        # resvg keeps the aspect ratio when given both dimensions, so a box
        # whose pixel size was rounded per side comes out a pixel short.
        canvas = Image.new("RGBA", tuple(size), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
        canvas.paste(im, (0, 0))
        im = canvas
    return im
