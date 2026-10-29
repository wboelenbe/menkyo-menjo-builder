"""Today's Inkscape output, reduced to the fixtures in reference/.

    python ref_render.py OUTDIR            (inside the reference image)

Run by make_reference.sh in a container built from Dockerfile.ref: Debian
bookworm, Inkscape 1.2.2, fonts-noto-cjk plus fonts-noto-cjk-extra (which
holds the crest's Noto Serif CJK JP SemiBold; the plain test image lacks it
and draws the ring in a fallback face).  MENKYO_SRC is a read-only snapshot of
the commit named in REF_COMMIT, the last one rendered by Inkscape.

For every case in refkit.CASES it runs that snapshot's own main() with
`-c example.toml` and writes:

    <case>-pdf150.png         the PDF, pdfium, 150 dpi, grey on white
    <case>-png.png            the PNG as written, composited on white, grey;
                              halved with refkit.half() when written at 300 dpi
    <case>-<column>.png       600 dpi crops of the PDF (pdfium): every text
                              column, whole, and the crest
    <case>-textlayer-graded.png
                              the inked cases' 600 dpi text layer after the
                              ink pass, alpha only (C-1, C-3; C-8's is C-1's).
                              The raw layer's alpha sum is in meta.json
    meta.json                 boxes, glyph cells, sizes, PDF and PNG facts,
                              and the toolchain that drew them

Only the shipped example configuration and stand-in names are used.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.environ.get("MENKYO_SRC", "/menkyo/src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                     # noqa: E402
from PIL import Image                                  # noqa: E402

import refkit                                          # noqa: E402
from menkyo import build_diploma as bd, config as config_mod, ink, paths  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
EXAMPLE = paths.resource("example.toml")
CFG = config_mod.load(EXAMPLE)


def layout(case):
    """Columns (key, x, y0, size, chars) and crop boxes in mm, from the
    snapshot's own constants and helpers."""
    bd.CFG = CFG
    drop = CFG.text_drop * bd.PAGE_H
    argv = refkit.CASES[case]
    get = lambda f: argv[argv.index(f) + 1] if f in argv else None
    award = CFG.award(get("-a"))
    name, rank, date = get("-n") or None, get("-r") or None, get("-d") or None
    rank_col = award.grade_column or bool(rank)
    rank = bd.rank_kanji(rank) if rank else None
    date = bd.date_column(date) if date else None
    xa, xr = bd.right_columns(rank_col)
    cols = [("heading", bd.X_HEADING, bd.Y_HEADING + drop, bd.SZ_HEADING, list(award.heading))]
    if name:
        chars = list(name) + list(CFG.honorific)
        cols.append(("name", xa, bd.Y_RANK + drop,
                     min(bd.SZ_AWARDEE, bd.AWARDEE_MAX_H / len(chars)), chars))
    if rank:
        cols.append(("rank", xr if name else bd.X_RANK, bd.Y_RANK + drop, bd.SZ_RANK, list(rank)))
    cols.append(("formula", bd.X_VERB, bd.Y_VERB + drop, bd.SZ_VERB, list(award.formula)))
    cols.append(("date", bd.X_DATE, bd.Y_BLOCK + drop, bd.SZ_DATE, date or bd.DATE_SLOTS))
    for key, x, sz, txt in (("art", bd.X_STYLE, bd.SZ_BLOCK, CFG.art),
                            ("dojo", bd.X_DOJO, bd.SZ_BLOCK, CFG.dojo),
                            ("title", bd.X_TITLE, bd.SZ_TITLE, CFG.signer_title),
                            ("signer", bd.X_SIGNER, bd.SZ_SIGNER, CFG.signer_name),
                            ("motto", bd.X_MOTTO, bd.SZ_MOTTO, CFG.motto)):
        if txt:
            cols.append((key, x, bd.Y_BLOCK + drop, sz, list(txt)))
    boxes = {}
    for key, x, y0, sz, chars in cols:
        boxes[key] = [x - 0.75 * sz, y0 - 0.75 * sz, x + 0.75 * sz, y0 + (len(chars) - 0.25) * sz]
    cx, cy = bd.CREST_C
    R = bd.CREST_R
    boxes["crest"] = [cx - 1.08 * R, cy - 1.08 * R, cx + 1.08 * R, cy + 1.08 * R]
    import math
    ring = []
    for text, step, sign, base in ((CFG.crest_ring, 34.0, 1, 90), (CFG.art, 30.0, -1, -90)):
        n = len(text)
        for i, ch in enumerate(text):
            ang = base - sign * step * (n - 1) / 2 + sign * i * step
            a = math.radians(ang)
            ring.append([ch, cx + bd.GLYPH_R * R * math.cos(a), cy + bd.GLYPH_R * R * math.sin(a)])
    columns = [dict(key=k, x=x, y0=y0, size=sz, chars=chars) for k, x, y0, sz, chars in cols]
    return columns, boxes, ring, dict(cx=cx, cy=cy, R=R)


def png_props(path):
    with Image.open(path) as im:
        a = im.getchannel("A") if im.mode in ("RGBA", "LA") else None
        return dict(size=list(im.size), mode=im.mode,
                    dpi=[round(float(v), 3) for v in im.info.get("dpi", (0, 0))],
                    alpha_extrema=list(a.getextrema()) if a else None,
                    corner_alpha=a.getpixel((5, 5)) if a else None,
                    bytes=os.path.getsize(path))


def run_case(case, out, fixtures):
    keep = {}
    real_ink, real_img = ink.ink_layer, bd._inked_text_image

    def ink_spy(src, dst, dpi, *a, **k):
        keep["raw"] = np.asarray(Image.open(src).convert("RGBA"))[..., 3].copy()
        r = real_ink(src, dst, dpi, *a, **k)
        keep["graded"] = np.asarray(Image.open(dst).convert("RGBA"))[..., 3].copy()
        return r

    def img_spy(*a, **k):
        el = real_img(*a, **k)
        keep["element"] = el
        return el

    ink.ink_layer, bd._inked_text_image = ink_spy, img_spy
    stamps = []
    t0 = time.perf_counter()
    try:
        bd.main(["-c", EXAMPLE, "--out", out] + refkit.CASES[case],
                progress=lambda e: stamps.append((e["stage"], time.perf_counter() - t0)))
    finally:
        ink.ink_layer, bd._inked_text_image = real_ink, real_img
    wall = time.perf_counter() - t0

    pdf = next((os.path.join(out, f) for f in os.listdir(out) if f.endswith(".pdf")), None)
    png = next((os.path.join(out, f) for f in os.listdir(out) if f.endswith(".png")), None)
    columns, boxes, ring, crest = layout(case)
    meta = dict(argv=refkit.CASES[case], variant=refkit.variant_of(case), wall_s=round(wall, 2),
                stages=stamps, columns=columns, boxes_mm=boxes, ring=ring, crest=crest)

    if png:
        meta["png"] = png_props(png)
        im = refkit.png_on_white(png)
        dpi = meta["png"]["dpi"][0]
        if dpi > 200:
            im = refkit.half(im)
        meta["png_fixture"] = dict(file=f"{case}-png.png", halved=dpi > 200, size=list(im.size))
        im.save(os.path.join(fixtures, f"{case}-png.png"), optimize=True)
    if pdf:
        meta["pdf"] = refkit.pdf_summary(pdf)
        meta["pdf"]["pdfium"] = list(refkit.pdf_info(pdf))
        meta["pdf"]["xref_problems"] = refkit.xref_problems(pdf)
        Image.fromarray(refkit.pdf_grey(pdf, 150)).save(
            os.path.join(fixtures, f"{case}-pdf150.png"), optimize=True)
        page = refkit.pdf_grey(pdf, 600)
        meta["crops"] = {}
        for key, box in boxes.items():
            x0, y0, x1, y1 = refkit.box_px(box, 600)
            Image.fromarray(page[y0:y1, x0:x1]).save(
                os.path.join(fixtures, f"{case}-{key}.png"), optimize=True)
            meta["crops"][key] = dict(file=f"{case}-{key}.png", box_px600=[x0, y0, x1, y1],
                                      ink=refkit.ink_sum(page[y0:y1, x0:x1]))
        del page
    if "graded" in keep and case != "C-8":          # C-8's is C-1's
        import re
        x, y, w, h = (float(v) for v in re.findall(
            r'(?:x|y|width|height)="([\d.]+)"', keep["element"]))
        meta["textlayer"] = dict(size=[int(keep["raw"].shape[1]), int(keep["raw"].shape[0])],
                                 bbox_mm=[x, y, w, h], element=keep["element"],
                                 raw_alpha_sum=int(keep["raw"].astype(np.int64).sum()),
                                 graded_alpha_sum=int(keep["graded"].astype(np.int64).sum()))
        Image.fromarray(keep["graded"]).save(
            os.path.join(fixtures, f"{case}-textlayer-graded.png"), optimize=True)
    return meta


def main():
    fixtures = sys.argv[1]
    os.makedirs(fixtures, exist_ok=True)
    tool = lambda *cmd: subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    import pypdfium2
    meta = dict(
        commit=os.environ.get("REF_COMMIT", "?"),
        inkscape=tool("inkscape", "--version"),
        crest_face=tool("fc-match", "Noto Serif CJK JP SemiBold"),
        body_face="Yuji Boku (the package's fonts/, via FONTCONFIG_FILE)",
        pypdfium2=getattr(pypdfium2, "PYPDFIUM_INFO", None) and str(pypdfium2.PYPDFIUM_INFO),
        note="argv after -c example.toml; rasters by refkit (pdfium), grey on white",
        cases={})
    for case in refkit.CASES:
        out = tempfile.mkdtemp(prefix=f"ref-{case}-")
        meta["cases"][case] = run_case(case, out, fixtures)
        shutil.rmtree(out)
        print(case, meta["cases"][case]["wall_s"], "s", flush=True)
    with open(os.path.join(fixtures, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
