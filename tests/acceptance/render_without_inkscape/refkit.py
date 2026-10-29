"""Comparison kit for render-without-inkscape (docs/work/render-without-inkscape/).

Used twice, with the same code, so a metric means the same on both sides:

- by ref_render.py, inside the Inkscape reference image, to reduce today's
  Inkscape output to the small fixtures in reference/;
- by tests/acceptance/test_ac_render_without_inkscape.py, to compare the
  new renderer's output with those fixtures and to inspect its PDFs.

Rasterising is pdfium (pypdfium2) on both sides, greyscale on white, at a
pixel size of round(page size x dpi / 72) per side.  Imports of numpy, scipy,
Pillow and pypdfium2 happen inside the functions, so this module imports on
any Python.

Nothing here reads a configuration: the cases name src/menkyo/example.toml
and stand-in names only.
"""

import re
import zlib

MM = 25.4

# ------------------------------------------------------------------ cases ---
# argv after `-c example.toml` (acceptance.md, "Cases"; the spike's IDs).
CASES = {
    "C-1": ["-a", "dan", "-v", "overlay", "-n", "ヤン・ヤンセン", "-r", "2",
            "-d", "2024-07-01", "-f", "pdf,png"],
    "C-3": ["-a", "shihan", "-v", "overlay", "-n", "ジョン・ドウ", "-r", "",
            "-d", "2024-07-01", "-f", "pdf,png"],
    "C-4": ["-a", "dan", "-v", "overlay-flat", "-n",
            "アレクサンドル・ファン・デル・フェルデン", "-r", "10",
            "-d", "2020-10-20", "-f", "pdf,png"],
    "C-4b": ["-a", "dan", "-v", "overlay-flat", "-n",
             "ピーター・ファン・デル・フェルデン", "-r", "10",
             "-d", "2020-10-20", "-f", "pdf,png"],
    "C-5": ["-a", "dan", "-v", "proof", "-n", "", "-r", "", "-d", "",
            "-f", "pdf,png"],
    "C-8": ["-a", "dan", "-v", "overlay", "-n", "ヤン・ヤンセン", "-r", "2",
            "-d", "2024-07-01", "-f", "png", "--dpi", "150"],
}
INKED = {"C-1", "C-3", "C-8"}
FLAT = {"C-4", "C-4b", "C-5"}


def variant_of(case):
    argv = CASES[case]
    return argv[argv.index("-v") + 1]


# ----------------------------------------------------------------- raster ---
def pdf_grey(path, dpi):
    """Page 1 of the PDF rendered by pdfium, greyscale on white, uint8 (H, W)."""
    import ctypes
    import numpy as np
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    doc = pdfium.PdfDocument(str(path))
    page = doc[0]
    pw, ph = page.get_size()
    W, H = round(pw * dpi / 72), round(ph * dpi / 72)
    bm = raw.FPDFBitmap_CreateEx(W, H, raw.FPDFBitmap_Gray, None, 0)
    try:
        raw.FPDFBitmap_FillRect(bm, 0, 0, W, H, 0xFFFFFFFF)
        m = raw.FS_MATRIX(W / pw, 0, 0, H / ph, 0, 0)
        clip = raw.FS_RECTF(0, 0, W, H)
        raw.FPDF_RenderPageBitmapWithMatrix(bm, page.raw, m, clip, 0)
        stride = raw.FPDFBitmap_GetStride(bm)
        buf = ctypes.cast(raw.FPDFBitmap_GetBuffer(bm),
                          ctypes.POINTER(ctypes.c_ubyte * (stride * H))).contents
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(H, stride)[:, :W].copy()
    finally:
        raw.FPDFBitmap_Destroy(bm)
        page.close()
        doc.close()
    return arr


def pdf_rgb(path, dpi):
    """Page 1 rendered by pdfium in colour on white, uint8 (H, W, 3)."""
    import numpy as np
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(path))
    page = doc[0]
    try:
        im = page.render(scale=dpi / 72, fill_color=(255, 255, 255, 255)).to_pil()
        return np.asarray(im.convert("RGB")).copy()
    finally:
        page.close()
        doc.close()


def pdf_info(path):
    """(page count, (width pt, height pt)) as pdfium reads it."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(path))
    try:
        n = len(doc)
        page = doc[0]
        size = page.get_size()
        page.close()
        return n, size
    finally:
        doc.close()


def png_on_white(path):
    """A PNG composited onto white, as an 'L' image."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB").convert("L")


def half(im):
    """Pillow's 2x2 box reduction; the same on both sides of a comparison."""
    return im.reduce(2)


# ---------------------------------------------------------------- metrics ---
def ssim(a, b, sigma=1.5, L=255.0):
    """Mean SSIM, Gaussian window (Wang et al. 2004), K1 = 0.01, K2 = 0.03."""
    import numpy as np
    from scipy import ndimage
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    C1, C2 = (0.01 * L) ** 2, (0.03 * L) ** 2
    f = lambda x: ndimage.gaussian_filter(x, sigma, truncate=3.5)
    ma, mb = f(a), f(b)
    va, vb, cab = f(a * a) - ma * ma, f(b * b) - mb * mb, f(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))
    return float(s.mean())


def mad(a, b):
    import numpy as np
    return float(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)).mean())


def xcorr_offset(a, b):
    """Sub-pixel (dy, dx) that moves b onto a, measured on ink (255 - grey)."""
    import numpy as np
    A = 255.0 - np.asarray(a, np.float64)
    B = 255.0 - np.asarray(b, np.float64)
    if A.sum() < 1 or B.sum() < 1:
        return 0.0, 0.0
    sh = [n * 2 for n in A.shape]
    r = np.fft.irfft2(np.fft.rfft2(A, sh) * np.conj(np.fft.rfft2(B, sh)), sh)
    r = np.fft.fftshift(r)
    py, px = np.unravel_index(np.argmax(r), r.shape)

    def para(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = para(r[py - 1, px], r[py, px], r[py + 1, px]) if 0 < py < r.shape[0] - 1 else 0.0
    dx = para(r[py, px - 1], r[py, px], r[py, px + 1]) if 0 < px < r.shape[1] - 1 else 0.0
    return float(py - sh[0] // 2 + dy), float(px - sh[1] // 2 + dx)


def align(a, b):
    """b moved onto a when the offset exceeds 0.1 px; (b, (dy, dx))."""
    import numpy as np
    from scipy import ndimage
    b = np.asarray(b, np.float64)
    dy, dx = xcorr_offset(a, b)
    if max(abs(dy), abs(dx)) > 0.1:
        b = ndimage.shift(b, (dy, dx), order=1, mode="nearest")
    return b, (dy, dx)


def same_shape(a, b):
    """Both arrays cut to their common top-left extent (pixel sizes may
    differ by a rounding pixel)."""
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    return a[:h, :w], b[:h, :w]


def box_px(box_mm, dpi):
    return tuple(int(round(v * dpi / MM)) for v in box_mm)


def crop(img, box_mm, dpi):
    x0, y0, x1, y1 = box_px(box_mm, dpi)
    return img[max(0, y0):y1, max(0, x0):x1]


def big_region_mm2(a, b, dpi):
    """Largest connected |a - b| > 64 region after a 3x3 opening, in mm²."""
    import numpy as np
    from scipy import ndimage
    m = np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)) > 64
    m = ndimage.binary_opening(m, structure=np.ones((3, 3)))
    lab, n = ndimage.label(m)
    if n == 0:
        return 0.0
    return float(np.bincount(lab.ravel())[1:].max() * (MM / dpi) ** 2)


def ink_sum(a):
    import numpy as np
    return float((255.0 - np.asarray(a, np.float64)).sum())


# ------------------------------------------------------------------- PDF ----
_OBJ = re.compile(rb"(?<![0-9])(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", re.S)
_TOKEN = re.compile(rb"/[^\s/\[\]()<>{}%]*|[-+]?(?:\d+\.?\d*|\.\d+)|<<|>>|\[|\]"
                    rb"|\([^)]*\)|<[0-9A-Fa-f\s]*>|[A-Za-z'\"][A-Za-z0-9*'\"]*")
COLOUR_OPS = {b"g", b"G", b"rg", b"RG", b"k", b"K", b"cs", b"CS", b"sc", b"SC",
              b"scn", b"SCN"}
PATH_OPS = {b"m", b"l", b"c", b"v", b"y", b"h", b"re"}


def _split_stream(body):
    """(dictionary bytes, raw stream bytes or None) for one object body."""
    m = re.search(rb"\bstream\r?\n", body)
    if not m:
        return body, None
    end = body.rfind(b"endstream")
    data = body[m.end():end]
    if data.endswith(b"\r\n"):
        data = data[:-2]
    elif data.endswith(b"\n"):
        data = data[:-1]
    return body[:m.start()], data


def _decode(dct, data):
    if data is None:
        return None
    if b"/FlateDecode" in dct:
        return zlib.decompress(data)
    if re.search(rb"/Filter", dct):
        return None             # an image codec: not needed here
    return data


def pdf_objects(path):
    """{object number: (dictionary bytes, decoded stream or None)}.

    Reads plain objects and, if present, compressed object streams.  Good
    enough for the files this package writes and for Inkscape's; not a
    general PDF parser.
    """
    raw_bytes = open(path, "rb").read()
    objs = {}
    for m in _OBJ.finditer(raw_bytes):
        dct, data = _split_stream(m.group(3))
        objs[int(m.group(1))] = (dct, _decode(dct, data))
    for num, (dct, data) in list(objs.items()):
        if b"/ObjStm" in dct and data is not None:
            n = int(re.search(rb"/N\s+(\d+)", dct).group(1))
            first = int(re.search(rb"/First\s+(\d+)", dct).group(1))
            head = data[:first].split()
            for i in range(n):
                onum, off = int(head[2 * i]), int(head[2 * i + 1])
                nxt = int(head[2 * i + 3]) if i + 1 < n else len(data) - first
                objs.setdefault(onum, (data[first + off:first + nxt], None))
    return raw_bytes, objs


def xref_problems(path):
    """Structural checks a strict reader makes: header, %%EOF, startxref, and
    every in-use cross-reference entry pointing at its object.  [] is clean."""
    data, objs = pdf_objects(path)
    out = []
    if not re.match(rb"%PDF-[12]\.\d", data):
        out.append("no %PDF-x.y header")
    if not data.rstrip().endswith(b"%%EOF"):
        out.append("does not end in %%EOF")
    m = list(re.finditer(rb"startxref\s+(\d+)", data))
    if not m:
        return out + ["no startxref"]
    at = int(m[-1].group(1))
    entries = []
    if data[at:at + 4] == b"xref":
        pos = at + 4
        trailer = data.find(b"trailer", pos)
        if trailer < 0:
            return out + ["xref table without trailer"]
        lines = data[pos:trailer].split(b"\n")
        start = None
        for line in lines:
            parts = line.split()
            if len(parts) == 2:
                start, i = int(parts[0]), 0
            elif len(parts) == 3 and start is not None:
                if parts[2] == b"n":
                    entries.append((start + i, int(parts[0])))
                i += 1
        tdict = data[trailer:data.find(b"startxref", trailer)]
        if b"/Root" not in tdict or b"/Size" not in tdict:
            out.append("trailer lacks /Root or /Size")
    else:
        mm = re.match(rb"(\d+)\s+0\s+obj", data[at:at + 40])
        if not mm or b"/XRef" not in objs.get(int(mm.group(1)), (b"",))[0]:
            return out + [f"startxref {at} points at neither xref nor an XRef stream"]
        dct, stream = objs[int(mm.group(1))]
        if b"/Root" not in dct:
            out.append("XRef stream lacks /Root")
        w = [int(v) for v in re.search(rb"/W\s*\[\s*([\d\s]+)\]", dct).group(1).split()]
        size = int(re.search(rb"/Size\s+(\d+)", dct).group(1))
        idx = re.search(rb"/Index\s*\[\s*([\d\s]+)\]", dct)
        ranges = [int(v) for v in idx.group(1).split()] if idx else [0, size]
        rec, pos = sum(w), 0
        for s, n in zip(ranges[::2], ranges[1::2]):
            for k in range(n):
                row = stream[pos:pos + rec]
                pos += rec
                f = [int.from_bytes(row[sum(w[:j]):sum(w[:j + 1])], "big") for j in range(3)]
                kind = f[0] if w[0] else 1
                if kind == 1:
                    entries.append((s + k, f[1]))
    for num, off in entries:
        if not re.match(rb"%d\s+\d+\s+obj" % num, data[off:off + 30]):
            out.append(f"xref entry for object {num} points at offset {off}, not at it")
    return out


def tokens(content):
    return _TOKEN.findall(content or b"")


def pdf_summary(path):
    """What the acceptance criteria look at in a PDF."""
    data, objs = pdf_objects(path)
    pages = [n for n, (d, _) in objs.items() if re.search(rb"/Type\s*/Page(?![s\w])", d)]
    images, fonts, groups = [], [], []
    for num, (d, _) in objs.items():
        if re.search(rb"/Subtype\s*/Image", d):
            cs = re.search(rb"/ColorSpace\s*(/\w+|\[[^\]]*\]|\d+\s+0\s+R)", d)
            sm = re.search(rb"/SMask\s+(\d+)\s+0\s+R", d)
            smask_cs = None
            if sm:
                sd = objs.get(int(sm.group(1)), (b"", None))[0]
                m2 = re.search(rb"/ColorSpace\s*(/\w+)", sd)
                smask_cs = m2.group(1).decode() if m2 else None
            images.append(dict(obj=num, cs=cs.group(1).decode() if cs else None,
                               smask=bool(sm), smask_cs=smask_cs,
                               is_smask=False))
        if re.search(rb"/Type\s*/Font\b|/FontFile[23]?\b|/FontDescriptor\b", d):
            fonts.append(num)
        # transparency groups, inline (/Group << ... >>) or as their own object
        for g in re.findall(rb"/Group\s*<<(.*?)>>", d, re.S) + (
                [d] if re.search(rb"/S\s*/Transparency", d)
                and not re.search(rb"/Group\s*<<", d) else []):
            cs = re.search(rb"/CS\s*(/\w+)", g)
            groups.append(cs.group(1).decode() if cs else None)
    smask_objs = {int(m) for d, _ in objs.values()
                  for m in re.findall(rb"/SMask\s+(\d+)\s+0\s+R", d)}
    for im in images:
        im["is_smask"] = im["obj"] in smask_objs
    # content streams: the pages' /Contents and every Form XObject
    content = set()
    for n in pages:
        c = re.search(rb"/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)", objs[n][0])
        if c:
            content |= {int(v) for v in re.findall(rb"(\d+)\s+0\s+R", c.group(1))}
    content |= {n for n, (d, _) in objs.items() if re.search(rb"/Subtype\s*/Form", d)}
    ops, paths, font_ops = {}, 0, 0
    for num, (d, stream) in objs.items():
        if num not in content or stream is None:
            continue
        toks = tokens(stream)
        for i, t in enumerate(toks):
            if t in COLOUR_OPS:
                key = t.decode()
                if t in (b"cs", b"CS") and i:
                    key += " " + toks[i - 1].decode()
                ops[key] = ops.get(key, 0) + 1
            elif t in PATH_OPS:
                paths += 1
            elif t in (b"Tf", b"Tj", b"TJ"):
                font_ops += 1
    mb = re.search(rb"/MediaBox\s*\[\s*([-\d.\s]+)\]", b"".join(
        objs[n][0] for n in pages) if pages else b"")
    rot = re.search(rb"/Rotate\s+(-?\d+)", b"".join(objs[n][0] for n in pages) if pages else b"")
    return dict(
        pages=len(pages),
        mediabox=[float(v) for v in mb.group(1).split()] if mb else None,
        rotate=int(rot.group(1)) if rot else 0,
        images=[i for i in images if not i["is_smask"]],
        smasks=[i for i in images if i["is_smask"]],
        font_objects=len(fonts), text_ops=font_ops,
        groups=groups, colour_ops=ops, path_ops=paths,
        size=len(data))
