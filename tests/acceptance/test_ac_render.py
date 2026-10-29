"""AC-13: real renders.

One run renders every variant of the dan certificate as PDF and PNG; the
tests look at what it wrote.

Rewritten for plain-white (docs/work/plain-white/acceptance.md, AC-19): the
three variants that remain, no press conversions, and nothing coloured.
Rewritten again for render-without-inkscape: there is no Inkscape to skip
for, and the PDFs are read with pypdfium2 and the kit in
render_without_inkscape/ instead of poppler.  The text is outlines now, so
"embeds Yuji Boku" became "outlines, no font" (that item's AC-12).
"""

import sys
from pathlib import Path

import pytest

import support

sys.path.insert(0, str(Path(__file__).resolve().parent / "render_without_inkscape"))
import refkit  # noqa: E402

pytestmark = pytest.mark.render

A3_PT = (420 / 25.4 * 72, 297 / 25.4 * 72)          # 1190.55 x 841.89
A3_PX_300 = (round(420 / 25.4 * 300), round(297 / 25.4 * 300))   # 4961 x 3508
TAG = "2-ヤン-ヤンセン"
VARIANTS = ["overlay", "overlay-flat", "proof"]


@pytest.fixture(scope="module")
def rendered(session_home, tmp_path_factory):
    out = tmp_path_factory.mktemp("render") / "out"
    r = support.run_menkyo(
        ["-c", support.EXAMPLE, "-a", "dan", "-v", ",".join(VARIANTS), "-f", "pdf,png",
         "-n", "ヤン・ヤンセン", "-r", "2", "-d", "2026-09-05", f"--out={out}", "--json"],
        env=support.isolated_env(session_home), cwd=out.parent, timeout=1800)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return {"out": out, "events": support.events(r.stdout), "stderr": r.stderr}


def f(rendered, variant, ext="pdf"):
    return rendered["out"] / f"dan-{variant}-{TAG}.{ext}"


def test_ac13_every_file_written(rendered):
    ev = rendered["events"]
    expected = []
    for v in VARIANTS:
        expected.append(f(rendered, v))
        expected.append(f(rendered, v, "png"))
    assert ev[-1] == {"event": "done", "out": str(rendered["out"]),
                      "files": [str(p) for p in expected]}
    progress = [e for e in ev if e["event"] == "progress"]
    # overlay: text, ink, pdf, png; overlay-flat and proof: pdf, png
    assert [p["step"] for p in progress] == list(range(1, 9))
    assert all(p["total"] == 8 for p in progress)
    assert {p["stage"] for p in progress} == {"text", "ink", "pdf", "png"}
    assert sorted(p.name for p in rendered["out"].iterdir()) == sorted(p.name for p in expected)


def test_ac13_pdfs_are_a3_landscape(rendered):
    for p in sorted(rendered["out"].glob("*.pdf")):
        assert p.read_bytes()[:5] == b"%PDF-", p
        pages, (w, h) = refkit.pdf_info(p)
        assert abs(w - A3_PT[0]) < 1 and abs(h - A3_PT[1]) < 1, (p.name, w, h)
        assert pages == 1, (p.name, pages)


def test_ac13_pngs_are_a3_at_300_dpi(rendered):
    from PIL import Image
    for v in VARIANTS:
        with Image.open(f(rendered, v, "png")) as im:
            assert abs(im.size[0] - A3_PX_300[0]) <= 1 and abs(im.size[1] - A3_PX_300[1]) <= 1, \
                (v, im.size)


def test_ac13_backgrounds(rendered):
    """overlay and overlay-flat: transparent, as before; the paper is white."""
    from PIL import Image
    for v in ("overlay", "overlay-flat"):
        with Image.open(f(rendered, v, "png")) as im:
            assert im.convert("RGBA").getpixel((5, 5))[3] == 0, v


def test_ac13_nothing_coloured(rendered):
    """The sheets themselves are black on white: no opaque pixel of the two
    print variants has any hue (no border, no tint).  The proof's guides are
    coloured on purpose and are not checked."""
    import numpy as np
    from PIL import Image
    for v in ("overlay", "overlay-flat"):
        with Image.open(f(rendered, v, "png")) as im:
            rgba = np.asarray(im.convert("RGBA")).astype(int)
        seen = rgba[..., 3] > 32
        chroma = rgba[..., :3].max(axis=2) - rgba[..., :3].min(axis=2)
        assert seen.sum() > 0, v
        assert int(chroma[seen].max()) <= 12, (v, int(chroma[seen].max()))
        rgb = refkit.pdf_rgb(f(rendered, v), 50).astype(int)
        assert int((rgb.max(axis=2) - rgb.min(axis=2)).max()) <= 12, f"{v}.pdf"


def _heading_ink(im, dpi):
    """Dark, opaque pixels in the heading column (x = 352 mm, y 76-152 mm)."""
    import numpy as np
    k = dpi / 25.4
    la = np.asarray(im.convert("LA").crop((round(347 * k), round(76 * k),
                                           round(357 * k), round(152 * k))))
    return int(((la[..., 1] > 128) & (la[..., 0] < 80)).sum() / (k * k))   # in mm²


def test_ac13_text_is_drawn(rendered):
    """The heading column carries ink on every variant, PNG and PDF alike.

    The inked variants place their text as an <image> raster; an Inkscape
    that ignores it leaves the column empty while the flat ones are fine.
    """
    from PIL import Image
    empty = {}
    for v in VARIANTS:
        with Image.open(f(rendered, v, "png")) as im:
            if _heading_ink(im, 300) < 100:
                empty[f"{v}.png"] = _heading_ink(im, 300)
        page = Image.fromarray(refkit.pdf_grey(f(rendered, v), 75))
        with page as im:
            if _heading_ink(im, 75) < 100:
                empty[f"{v}.pdf"] = _heading_ink(im, 75)
    assert not empty, f"no text in the heading column (mm² of ink): {empty}"


def test_ac13_flat_pdf_text_is_outlines(rendered):
    """Was: the flat PDF embeds Yuji Boku.  The text is glyph outlines now,
    so there is no font to embed and the check is that none is."""
    for v in ("overlay-flat", "proof"):
        s = refkit.pdf_summary(f(rendered, v))
        assert s["font_objects"] == 0 and s["text_ops"] == 0, (v, s)
        assert s["path_ops"] > 1000, (v, s["path_ops"])


def test_ac13_inked_svg_carries_its_raster(session_home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", support.EXAMPLE, "-a", "shihan", "-v", "overlay", "-f", "svg",
                            "-d", "", f"--out={out}"], support.isolated_env(session_home),
                           tmp_path, timeout=900)
    assert r.returncode == 0, r.stderr
    svg = (out / "shihan-overlay-sample.svg").read_text(encoding="utf-8")
    # xlink:href with xlink declared on the root, so the SVG still opens in
    # Inkscape 1.2, which ignores a plain href (packaging, F-3).
    assert 'xlink:href="shihan-overlay-sample-textlayer.png"' in svg
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" '
                          'xmlns:xlink="http://www.w3.org/1999/xlink" ')
    from PIL import Image
    with Image.open(out / "shihan-overlay-sample-textlayer.png") as im:
        assert im.mode == "RGBA" and im.size[0] > 1000
