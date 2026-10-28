"""Metrics and comparison images for the no-inkscape spike (D-3).

    python compare.py REF CAND IMGDIR METRICS.json [--label NAME]

REF and CAND are the output trees of ref_driver.py and render_candidate.py
(one directory per case, each with keep/). Computes, per acceptance.md:

    V-1  whole page, both PDFs rasterised by pdfium at 150 dpi; SSIM and mean
         |diff|; the same on the PNGs each route wrote (reported only)
    V-2  600 dpi crops (heading, name, rank, date bottom, crest): SSIM and the
         largest connected |diff| > 64 region after a 3x3 (0.127 mm) opening
    G-1  per glyph cell, flat cases at 600 dpi: sub-pixel offset by FFT
         cross-correlation with a parabolic peak fit, after global alignment
    G-3  crest crop (as V-2) plus each ring glyph's ink centroid
    G-5  ink coverage per column in C-4
    V-3  the text layer before ink_layer: size, bbox, IoU(alpha > 128),
         total alpha; after it: mean graded alpha, share below 0.9
    V-4  median colour of solid interior text-layer pixels, CIEDE2000

    python compare.py viewers CAND VIEWERDIR OUT.json      F-4, after viewers.sh

and writes, per case, IMGDIR/<case>_<variant>_side-by-side.png (100 dpi,
Inkscape left) and IMGDIR/<case>_crops.png (600 dpi: Inkscape, candidate,
|diff| x 4 in red).

Grey is Pillow's convert("L") of the image composited on white. Alignment:
a global sub-pixel offset is measured and reported; it is applied (linear
interpolation) only when it exceeds 0.1 px, which it never did here.
"""
import json, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.environ.get("MENKYO_SRC", "/menkyo/src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menkyo import build_diploma as bd, config as config_mod, paths  # noqa: E402
import norender as nr  # noqa: E402
from cases import CASES  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
CFG = config_mod.load(paths.resource("example.toml"))
bd.CFG = CFG
DROP = CFG.text_drop * bd.PAGE_H
MM = 25.4


# ---------------------------------------------------------------- helpers ---
def find(d, ext):
    fs = [f for f in os.listdir(d) if f.endswith(ext) and not f.endswith("-textlayer.png")]
    return os.path.join(d, fs[0]) if fs else None


def pdf_grey(path, dpi):
    """The PDF rasterised by pdfium on white, as greyscale float."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    page = pdf[0]
    w, h = page.get_size()
    size = (round(w * dpi / 72), round(h * dpi / 72))
    page.close(); pdf.close()
    im = nr.rasterise(open(path, "rb").read(), size, transparent=False)
    return np.asarray(im.convert("RGB").convert("L"), dtype=np.float64)


def png_grey(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB").convert("L"), dtype=np.float64)


def ssim(a, b, sigma=1.5, L=255.0):
    """Mean SSIM, Gaussian window (Wang et al. 2004), K1 = 0.01, K2 = 0.03."""
    C1, C2 = (0.01 * L) ** 2, (0.03 * L) ** 2
    f = lambda x: ndimage.gaussian_filter(x, sigma, truncate=3.5)
    ma, mb = f(a), f(b)
    va, vb, cab = f(a * a) - ma * ma, f(b * b) - mb * mb, f(a * b) - ma * mb
    s = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))
    return float(s.mean())


def xcorr_offset(a, b):
    """Sub-pixel (dy, dx) that moves b onto a, on ink (255 - grey)."""
    A, B = 255.0 - a, 255.0 - b
    if A.sum() < 1 or B.sum() < 1:
        return 0.0, 0.0
    sh = [n * 2 for n in a.shape]
    r = np.fft.irfft2(np.fft.rfft2(A, sh) * np.conj(np.fft.rfft2(B, sh)), sh)
    r = np.fft.fftshift(r)
    py, px = np.unravel_index(np.argmax(r), r.shape)
    def para(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = para(r[py - 1, px], r[py, px], r[py + 1, px]) if 0 < py < r.shape[0] - 1 else 0
    dx = para(r[py, px - 1], r[py, px], r[py, px + 1]) if 0 < px < r.shape[1] - 1 else 0
    return py - sh[0] // 2 + dy, px - sh[1] // 2 + dx


def align(a, b):
    dy, dx = xcorr_offset(a, b)
    if max(abs(dy), abs(dx)) > 0.1:
        b = ndimage.shift(b, (dy, dx), order=1, mode="nearest")
    return b, (round(dy, 3), round(dx, 3))


def crop(img, box_mm, dpi):
    x0, y0, x1, y1 = (int(round(v * dpi / MM)) for v in box_mm)
    return img[max(0, y0):y1, max(0, x0):x1]


def big_region_mm2(a, b, dpi):
    m = np.abs(a - b) > 64
    m = ndimage.binary_opening(m, structure=np.ones((3, 3)))
    lab, n = ndimage.label(m)
    if n == 0:
        return 0.0
    px = np.bincount(lab.ravel())[1:].max()
    return float(px * (MM / dpi) ** 2)


# ------------------------------------------------------------- geometry -----
def layout(case):
    """Columns, crops and ring glyphs (mm) for a case, from build_diploma."""
    argv = CASES[case]
    get = lambda f: argv[argv.index(f) + 1] if f in argv else None
    award = CFG.award(get("-a"))
    name, rank, date = get("-n") or None, get("-r") or None, get("-d") or None
    rank_col = award.grade_column or bool(rank)
    rank = bd.rank_kanji(rank) if rank else None
    date = bd.date_column(date) if date else None
    xa, xr = bd.right_columns(rank_col)
    cols = [("heading", bd.X_HEADING, bd.Y_HEADING + DROP, bd.SZ_HEADING, list(award.heading))]
    if name:
        chars = list(name) + list(CFG.honorific)
        cols.append(("name", xa, bd.Y_RANK + DROP,
                     min(bd.SZ_AWARDEE, bd.AWARDEE_MAX_H / len(chars)), chars))
    if rank:
        cols.append(("rank", xr if name else bd.X_RANK, bd.Y_RANK + DROP, bd.SZ_RANK, list(rank)))
    cols.append(("formula", bd.X_VERB, bd.Y_VERB + DROP, bd.SZ_VERB, list(award.formula)))
    cols.append(("date", bd.X_DATE, bd.Y_BLOCK + DROP, bd.SZ_DATE, date or bd.DATE_SLOTS))
    for key, x, sz, txt in (("art", bd.X_STYLE, bd.SZ_BLOCK, CFG.art), ("dojo", bd.X_DOJO, bd.SZ_BLOCK, CFG.dojo),
                            ("title", bd.X_TITLE, bd.SZ_TITLE, CFG.signer_title),
                            ("signer", bd.X_SIGNER, bd.SZ_SIGNER, CFG.signer_name),
                            ("motto", bd.X_MOTTO, bd.SZ_MOTTO, CFG.motto)):
        if txt:
            cols.append((key, x, bd.Y_BLOCK + DROP, sz, list(txt)))
    crops = {}
    for key, x, y0, sz, chars in cols:
        n = len(chars)
        if key == "heading":
            crops["heading"] = (x - 0.65 * sz, y0 - 0.6 * sz, x + 0.65 * sz, y0 + 2.6 * sz)
        elif key in ("name", "rank"):
            crops[key] = (x - 0.65 * sz, y0 - 0.6 * sz, x + 0.65 * sz, y0 + (n - 0.4) * sz)
        elif key == "date":
            crops["date bottom"] = (x - 0.65 * sz, y0 + (n - 4.6) * sz, x + 0.65 * sz, y0 + (n - 0.4) * sz)
    cx, cy = bd.CREST_C
    R = bd.CREST_R
    crops["crest"] = (cx - 1.08 * R, cy - 1.08 * R, cx + 1.08 * R, cy + 1.08 * R)
    import math
    ring = []
    for text, step, sign, base in ((CFG.crest_ring, 34.0, 1, 90), (CFG.art, 30.0, -1, -90)):
        n = len(text)
        for i, ch in enumerate(text):
            ang = base - sign * step * (n - 1) / 2 + sign * i * step
            a = math.radians(ang)
            ring.append((ch, cx + bd.GLYPH_R * R * math.cos(a), cy + bd.GLYPH_R * R * math.sin(a)))
    return cols, crops, ring


def glyph_cells(cols):
    for key, x, y0, sz, chars in cols:
        for i, ch in enumerate(chars):
            if ch is not None:
                cy = y0 + i * sz
                yield key, ch, (x - 0.5 * sz, cy - 0.5 * sz, x + 0.5 * sz, cy + 0.5 * sz)


# ---------------------------------------------------------------- metrics ---
def page_metrics(case, ref, cand, out):
    res = {}
    rp, cp = find(ref, ".pdf"), find(cand, ".pdf")
    if rp and cp:
        a, b = pdf_grey(rp, 150), pdf_grey(cp, 150)
        b, off = align(a, b)
        res["V-1 pdf150"] = dict(ssim=round(ssim(a, b), 5), mad=round(float(np.abs(a - b).mean()), 4), offset_px=off)
    rn, cn = find(ref, ".png"), find(cand, ".png")
    if rn and cn:
        a, b = png_grey(rn), png_grey(cn)
        b, off = align(a, b)
        res["V-1 png"] = dict(ssim=round(ssim(a, b), 5), mad=round(float(np.abs(a - b).mean()), 4),
                              offset_px=off, size_ref=Image.open(rn).size, size_cand=Image.open(cn).size)
    return res


def crop_metrics(case, ref, cand, imgdir, label):
    rp, cp = find(ref, ".pdf"), find(cand, ".pdf")
    if not (rp and cp):
        return {}
    A, B = pdf_grey(rp, 600), pdf_grey(cp, 600)
    _, goff = align(A[::4, ::4], B[::4, ::4])
    cols, crops, ring = layout(case)
    res = {"global_offset_px600": [v * 4 for v in goff], "V-2": {}}
    panels = []
    for key, box in crops.items():
        a, b = crop(A, box, 600), crop(B, box, 600)
        b2, off = align(a, b)
        res["V-2"][key] = dict(ssim=round(ssim(a, b2), 4), max_region_mm2=round(big_region_mm2(a, b2, 600), 4),
                               offset_px=off)
        panels.append((key, a, b2))
    # G-3: each ring glyph's ink centroid, inside the band between the rings
    R = bd.CREST_R
    cx, cy = bd.CREST_C
    g3 = []
    for ch, gx, gy in ring:
        box = (gx - 0.16 * R, gy - 0.16 * R, gx + 0.16 * R, gy + 0.16 * R)
        a, b = crop(A, box, 600), crop(B, box, 600)
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        px, py = box[0] + (xx + 0.5) * MM / 600, box[1] + (yy + 0.5) * MM / 600
        rr = np.hypot(px - cx, py - cy) / R
        band = (rr > 0.68) & (rr < 0.985)
        cen = []
        for im in (a, b):
            w = (255 - im) * band
            cen.append((float((w * px).sum() / w.sum()), float((w * py).sum() / w.sum())))
        g3.append(dict(ch=ch, d_mm=round(float(np.hypot(cen[0][0] - cen[1][0], cen[0][1] - cen[1][1])), 4)))
    res["G-3 ring"] = g3
    # G-1: per glyph cell (flat cases only)
    if "flat" in rp or "proof" in rp:
        worst, offs = None, []
        for key, ch, box in glyph_cells(cols):
            a, b = crop(A, box, 600), crop(B, box, 600)
            dy, dx = xcorr_offset(a, b)
            d = float(np.hypot(dy, dx) * MM / 600)
            offs.append(d)
            if worst is None or d > worst[2]:
                worst = (key, ch, d, (round(dy, 3), round(dx, 3)))
        res["G-1"] = dict(glyphs=len(offs), worst=dict(column=worst[0], ch=worst[1], d_mm=round(worst[2], 4),
                                                       dy_dx_px600=worst[3]),
                          median_mm=round(float(np.median(offs)), 4))
        # G-5: ink per column
        g5 = {}
        for key, x, y0, sz, chars in cols:
            box = (x - 0.75 * sz, y0 - sz, x + 0.75 * sz, y0 + len(chars) * sz)
            a, b = crop(A, box, 600), crop(B, box, 600)
            ia, ib = (255 - a).sum(), (255 - b).sum()
            if ia > 0:
                g5[key] = round(float((ib - ia) / ia * 100), 3)
        res["G-5 ink % diff"] = g5
    crop_sheet(panels, os.path.join(imgdir, f"{case}_crops.png"), case, label)
    return res


def textlayer_metrics(ref, cand):
    rk, ck = os.path.join(ref, "keep"), os.path.join(cand, "keep")
    if not os.path.exists(os.path.join(rk, "textlayer-raw.png")):
        return {}
    import re
    el = lambda d: [float(v) for v in re.findall(r'(?:x|y|width|height)="([\d.]+)"', open(os.path.join(d, "image-element.txt")).read())]
    ra, ca = (np.asarray(Image.open(os.path.join(d, "textlayer-raw.png")).convert("RGBA")) for d in (rk, ck))
    rg, cg = (np.asarray(Image.open(os.path.join(d, "textlayer-graded.png")).convert("RGBA")) for d in (rk, ck))
    h, w = min(ra.shape[0], ca.shape[0]), min(ra.shape[1], ca.shape[1])
    ma, mb = ra[:h, :w, 3] > 128, ca[:h, :w, 3] > 128
    out = {"V-3": dict(
        size_ref=[ra.shape[1], ra.shape[0]], size_cand=[ca.shape[1], ca.shape[0]],
        bbox_ref_mm=el(rk), bbox_cand_mm=el(ck),
        bbox_max_diff_mm=round(max(abs(p - q) for p, q in zip(el(rk), el(ck))), 4),
        iou=round(float((ma & mb).sum() / (ma | mb).sum()), 5),
        total_alpha_diff_pct=round(float((ca[..., 3].astype(np.int64).sum() / ra[..., 3].astype(np.int64).sum() - 1) * 100), 3),
    )}
    g = {}
    for k, raw_, gr in (("ref", ra, rg), ("cand", ca, cg)):
        inkpx = raw_[..., 3] >= 128
        ga = gr[..., 3][inkpx].astype(np.float64) / 255
        g[k] = (float(ga.mean()), float((ga < 0.9).mean()))
    out["V-3"]["graded_mean_alpha"] = [round(g["ref"][0], 5), round(g["cand"][0], 5)]
    out["V-3"]["graded_mean_diff"] = round(g["cand"][0] - g["ref"][0], 5)
    out["V-3"]["share_below_0.9"] = [round(g["ref"][1] * 100, 3), round(g["cand"][1] * 100, 3)]
    out["V-3"]["share_diff_pp"] = round((g["cand"][1] - g["ref"][1]) * 100, 3)
    med = []
    for raw_ in (ra, ca):
        solid = ndimage.binary_erosion(raw_[..., 3] == 255, iterations=2)
        med.append(np.median(raw_[..., :3][solid], axis=0))
    out["V-4"] = dict(median_rgb_ref=med[0].tolist(), median_rgb_cand=med[1].tolist(),
                      dE2000=round(de2000(med[0], med[1]), 4))
    return out


def de2000(c1, c2):
    def lab(c):
        c = np.asarray(c, float) / 255
        c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
        M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]])
        x, y, z = M @ c / np.array([0.95047, 1.0, 1.08883])
        f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
        return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))
    import math
    L1, a1, b1 = lab(c1); L2, a2, b2 = lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hb = (h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2
    if C1p * C2p == 0: hb = h1p + h2p
    T = 1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb)) \
        + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.2 * math.cos(math.radians(4 * hb - 63))
    SL = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


# ----------------------------------------------------------------- images ---
def _font(px):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


def side_by_side(case, ref, cand, imgdir, label):
    """Whole page, 100 dpi, Inkscape left and the candidate right."""
    rn, cn = find(ref, ".png"), find(cand, ".png")
    if not (rn and cn):
        return None
    W, H = round(420 * 100 / MM), round(297 * 100 / MM)
    ims = []
    for p in (rn, cn):
        im = Image.open(p).convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        ims.append(bg.convert("L").resize((W, H), Image.LANCZOS))
    head = 60
    sheet = Image.new("L", (2 * W + 30, H + head), 255)
    d = ImageDraw.Draw(sheet)
    variant = [a for a in CASES[case] if a in ("overlay", "overlay-flat", "proof")][0]
    for i, (im, t) in enumerate(zip(ims, ("Inkscape 1.2.2 (reference)", f"{label} (candidate)"))):
        x = i * (W + 30)
        sheet.paste(im, (x, head))
        d.rectangle([x, head, x + W - 1, head + H - 1], outline=170)
        d.text((x + 8, 12), f"{case}  {variant}  {t}  - PNG as written, 100 dpi", fill=0, font=_font(30))
    name = f"{case}_{variant}_side-by-side.png"
    sheet.quantize(32, dither=Image.Dither.NONE).save(os.path.join(imgdir, name), optimize=True)
    return name


def crop_sheet(panels, path, case, label):
    """V-2 crops at 600 dpi: Inkscape | candidate | |diff| x 4 (red)."""
    pad, head, lab = 24, 70, 54
    rows = []
    for key, a, b in panels:
        # long name columns are split in pieces of about 70 mm so the sheet stays legible
        step = int(70 * 600 / MM)
        for i in range(0, a.shape[0], step):
            part = f"{key}" + (f" ({i // step + 1}/{-(-a.shape[0] // step)})" if a.shape[0] > step else "")
            rows.append((part, a[i:i + step], b[i:i + step]))
    # lay rows out left to right, wrapping at ~5200 px
    tiles, x, y, rowh, maxw = [], pad, head, 0, 5200
    for part, a, b in rows:
        w = a.shape[1] * 3 + 2 * pad
        if x + w > maxw and x > pad:
            x, y, rowh = pad, y + rowh + lab + pad, 0
        tiles.append((part, a, b, x, y))
        x += w + 3 * pad
        rowh = max(rowh, a.shape[0])
    Wt, Ht = max(t[3] + t[1].shape[1] * 3 + 2 * pad for t in tiles) + pad, y + rowh + lab + pad
    sheet = Image.new("RGB", (Wt, Ht), "white")
    d = ImageDraw.Draw(sheet)
    d.text((pad, 14), f"{case}: 600 dpi crops, PDF rasterised by pdfium.  Each: Inkscape | {label} | |diff| x 4 (red)",
           fill="black", font=_font(40))
    for part, a, b, x, y in tiles:
        d.text((x, y + 4), part, fill="black", font=_font(34))
        yy = y + lab
        A = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        B = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))
        diff = np.clip(np.abs(a - b) * 4, 0, 255).astype(np.uint8)
        D = Image.merge("RGB", [Image.new("L", A.size, 255), Image.fromarray(255 - diff), Image.fromarray(255 - diff)])
        for k, im in enumerate((A.convert("RGB"), B.convert("RGB"), D)):
            xx = x + k * (a.shape[1] + pad)
            sheet.paste(im, (xx, yy))
            d.rectangle([xx - 1, yy - 1, xx + a.shape[1], yy + a.shape[0]], outline=(160, 160, 160))
    sheet.quantize(48, dither=Image.Dither.NONE).save(path, optimize=True)


def viewers(cand, vdir, out):
    """F-4: each viewer's 150 dpi raster against the candidate's own PNG.

    The own PNG (300 dpi) is composited on white and box-filtered to the
    150 dpi grid. Ink coverage is mean(1 - L/255) over the union of the text
    columns' boxes from layout().
    """
    res = {}
    for case in ("C-1", "C-3", "C-4", "C-5"):
        own = Image.fromarray(png_grey(find(os.path.join(cand, case), ".png")).astype(np.uint8))
        cols, _, _ = layout(case)
        bx = (min(x - 0.6 * sz for _, x, y0, sz, ch in cols), min(y0 - 0.6 * sz for _, x, y0, sz, ch in cols),
              max(x + 0.6 * sz for _, x, y0, sz, ch in cols), max(y0 + len(ch) * sz for _, x, y0, sz, ch in cols))
        res[case] = {}
        views = {"pdfium": pdf_grey(os.path.join(vdir, f"{case}.pdf"), 150)}
        for v in ("gs", "poppler", "sips", "quartz"):
            p = os.path.join(vdir, f"{case}-{v}.png")
            if os.path.exists(p):
                views[v] = png_grey(p)
        for v, img in views.items():
            ref = np.asarray(own.resize((img.shape[1], img.shape[0]), Image.BOX), dtype=np.float64)
            img2, off = align(ref, img)
            cov = lambda im: float((1 - crop(im, bx, 150) / 255).mean())
            res[case][v] = dict(size=[img.shape[1], img.shape[0]], ssim=round(ssim(ref, img2), 4),
                                ink_own=round(cov(ref), 4), ink_viewer=round(cov(img2), 4),
                                ink_diff=round(cov(img2) - cov(ref), 4), offset_px=off)
        print(case, json.dumps(res[case]))
    json.dump(res, open(out, "w"), indent=1)


# ------------------------------------------------------------------- main ---
def main():
    if sys.argv[1] == "viewers":
        return viewers(*sys.argv[2:5])
    ref, cand, imgdir, out = sys.argv[1:5]
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "candidate"
    only = sys.argv[sys.argv.index("--cases") + 1].split(",") if "--cases" in sys.argv else None
    images = "--no-images" not in sys.argv
    os.makedirs(imgdir, exist_ok=True)
    allres = {}
    for case in sorted(CASES):
        r, c = os.path.join(ref, case), os.path.join(cand, case)
        if (only and case not in only) or not (os.path.isdir(r) and os.path.isdir(c)) or not find(c, ".png"):
            continue
        res = page_metrics(case, r, c, imgdir)
        if images:
            res["side_by_side"] = side_by_side(case, r, c, imgdir, label)
            res.update(crop_metrics(case, r, c, imgdir, label))
        res.update(textlayer_metrics(r, c))
        allres[case] = res
        print(case, json.dumps(res, ensure_ascii=False))
    json.dump(allres, open(out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
