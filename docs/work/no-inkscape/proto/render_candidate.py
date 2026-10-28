"""Candidate renders: menkyo's own CLI with Inkscape swapped for norender.

    python render_candidate.py OUT CASE [CASE ...]        cases from cases.py
    python render_candidate.py --cli -- ARGV...           one raw CLI run

menkyo is imported read-only (MENKYO_SRC, default: a snapshot of HEAD's
src/); only three of its functions are replaced, and only at runtime:

    _font_env           no fontconfig: there is nothing to configure
    _inked_text_image   the text layer: outlines -> PDF -> pdfium, 600 dpi
    render              PDF from the outlined SVG, PNG by pdfium from that PDF

Everything else is menkyo's: document(), ink.ink_layer(), the flags, the
--json events, the progress stages and their totals, the file names.

SPIKE_RASTER=resvg switches the raster step to the runner-up (resvg-py on the
outlined SVG); the PDF is the same either way. The text-layer PNG before and
after ink.ink_layer, the <image> element, the stage times (S-3) and the
glyph list (G-1) are kept under OUT/<case>/keep, as ref_driver.py does.
"""
import json, os, shutil, sys, time

sys.path.insert(0, os.environ.get("MENKYO_SRC", "/menkyo/src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menkyo import build_diploma as bd, ink, paths  # noqa: E402
import norender as nr  # noqa: E402

RASTER = os.environ.get("SPIKE_RASTER", "pdfium")
KEEP = None             # set per case by the driver
GLYPHS = []


def _raster(svg_outlined, pdf_bytes, size, transparent, base_dir, area=None, grey=False):
    if RASTER == "resvg":
        im = nr.rasterise_resvg(svg_outlined, size, transparent, base_dir, area)
        if grey:                                    # coverage, as black on white
            a = im.getchannel("A")
            return a.point(lambda v: 255 - v)
        return im
    return nr.rasterise(pdf_bytes, size, transparent, grey=grey)


def inked_text_image(base, verb, heading, kw, env, supersample=1):
    """Stand-in for build_diploma._inked_text_image, without Inkscape."""
    bd.PROGRESS("text")
    tmp = base + "-textlayer"
    # In its own frame, so the render's buffers are gone before ink_layer,
    # which is the peak of the whole run.
    x, y, w, h = _text_layer(verb, heading, kw, supersample, tmp + ".png")
    bd.PROGRESS("ink")
    ink.ink_layer(tmp + ".png", tmp + ".png", bd.INK_DPI)
    if KEEP:
        shutil.copy(tmp + ".png", os.path.join(KEEP["dir"], "textlayer-graded.png"))
    el = (f'<image x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
          f'xlink:href="{os.path.basename(tmp)}.png" preserveAspectRatio="none"/>')
    if KEEP:
        open(os.path.join(KEEP["dir"], "image-element.txt"), "w").write(el)
    return el


def _text_layer(verb, heading, kw, supersample, png):
    """The text alone, as coverage at INK_DPI, saved as #111111 + alpha."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    svg = bd.document(verb, heading, layer="text", **kw)
    outlined, bbox = nr.outline_svg(svg, GLYPHS)
    x, y, w, h = bbox
    # Pixel size as Inkscape's --export-area-drawing makes it: the bbox at
    # INK_DPI, rounded; the bbox itself is the exact outline bounds.
    target = (max(1, round(w * bd.INK_DPI / 25.4)), max(1, round(h * bd.INK_DPI / 25.4)))
    size = (target[0] * supersample, target[1] * supersample)
    pdf = nr.svg_to_pdf(outlined, area=bbox, fill_override="#000000")
    cov = _raster(outlined.replace('fill="#111111"', 'fill="#000000"'), pdf, size,
                  True, ".", area=bbox, grey=True)
    if KEEP:
        KEEP["supersample_px"] = list(size)
    cov = cov.point(lambda v: 255 - v)                 # black on white -> coverage
    if supersample > 1:
        cov = cov.resize(target, Image.LANCZOS)
    rgba = Image.merge("RGBA", [Image.new("L", target, 0x11)] * 3 + [cov])
    rgba.save(png, dpi=(bd.INK_DPI, bd.INK_DPI))
    if KEEP:
        shutil.copy(png, os.path.join(KEEP["dir"], "textlayer-raw.png"))
    return x, y, w, h


def render(svg_path, out_base, formats, press=False, dpi=300,
           transparent=False, convert="gray"):
    """Stand-in for build_diploma.render: PDF and PNG with no external tool."""
    svg = open(svg_path, encoding="utf-8").read()
    base_dir = os.path.dirname(svg_path)
    written, pdf = [], None
    # The stage is announced before its work, so the PDF's time counts as
    # "pdf" -- or as "png" when only a PNG is asked for.
    bd.PROGRESS("pdf" if "pdf" in formats else "png")
    if "pdf" in formats or "png" in formats:
        outlined, _ = nr.outline_svg(svg, GLYPHS)
        pdf = nr.svg_to_pdf(outlined, base_dir)
    if "pdf" in formats:
        open(out_base + ".pdf", "wb").write(pdf)
        written.append(out_base + ".pdf")
        # --press is out of the spike's scope (plain-white removes it).
    if "png" in formats:
        if "pdf" in formats:
            bd.PROGRESS("png")
        size = (round(bd.PAGE_W * dpi / 25.4), round(bd.PAGE_H * dpi / 25.4))
        im = _raster(outlined, pdf, size, transparent, base_dir)
        im.save(out_base + ".png", dpi=(dpi, dpi))
        written.append(out_base + ".png")
    if "svg" in formats:                       # unchanged: <text>, as today
        shutil.copy(svg_path, out_base + ".svg")
        written.append(out_base + ".svg")
        side = svg_path[:-4] + "-textlayer.png"
        if os.path.exists(side):
            shutil.copy(side, out_base + "-textlayer.png")
            written.append(out_base + "-textlayer.png")
    return written


def patch():
    bd._font_env = lambda: {}
    bd._inked_text_image = inked_text_image
    bd.render = render
    # Fail on a bad font file before the first progress event (G-6).
    real_main = bd.main
    def main(argv=None, progress=None):
        nr.check_fonts()
        return real_main(argv, progress)
    bd.main = main


def run_cases(out_root, cases):
    global KEEP
    from cases import CASES
    example = os.environ.get("SPIKE_CONFIG") or paths.resource("example.toml")
    for case in cases:
        out = os.path.join(out_root, case)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(os.path.join(out, "keep"))
        KEEP = {"dir": os.path.join(out, "keep")}
        GLYPHS.clear()
        stamps = []
        t0 = time.perf_counter()
        argv = ["-c", example, "--out", out] + CASES[case]
        try:
            bd.main(argv, progress=lambda e: stamps.append((e["stage"], time.perf_counter() - t0)))
            status = "ok"
        except SystemExit as e:
            status = f"exit: {e.code}"
        wall = time.perf_counter() - t0
        json.dump({"argv": argv, "wall": wall, "stages": stamps, "status": status,
                   "raster": RASTER, "fonts": {k: v[0] for k, v in nr.font_paths().items()},
                   "supersample_px": KEEP.get("supersample_px")},
                  open(os.path.join(out, "stages.json"), "w"), ensure_ascii=False, indent=1)
        json.dump(GLYPHS, open(os.path.join(out, "keep", "glyphs.json"), "w"),
                  ensure_ascii=False, indent=0)
        print(case, f"{wall:.2f}s", status, sorted(f for f in os.listdir(out) if f != "keep"))


if __name__ == "__main__":
    patch()
    if sys.argv[1] == "--cli":
        sys.exit(bd.cli(sys.argv[3:] if sys.argv[2] == "--" else sys.argv[2:]))
    run_cases(sys.argv[1], sys.argv[2:])
