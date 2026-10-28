"""AC-13: real renders with Inkscape and Ghostscript.

Skipped where Inkscape is missing (a Mac without it); failed instead under
REQUIRE_RENDER=1, which the Docker test image and the release workflow set.
One run renders every variant of the dan certificate, with --press, as PDF
and PNG; the tests look at what it wrote.
"""

import re
import subprocess

import pytest

import support
from conftest import require_program

pytestmark = pytest.mark.render

A3_PT = (420 / 25.4 * 72, 297 / 25.4 * 72)          # 1190.55 x 841.89
A3_PX_300 = (round(420 / 25.4 * 300), round(297 / 25.4 * 300))   # 4961 x 3508
TAG = "2-ヤン-ヤンセン"
VARIANTS = ["overlay", "full", "full-cream", "overlay-flat", "full-flat", "proof"]


@pytest.fixture(scope="module")
def rendered(inkscape, ghostscript, session_home, tmp_path_factory):
    out = tmp_path_factory.mktemp("render") / "out"
    r = support.run_menkyo(
        ["-c", support.EXAMPLE, "-a", "dan", "-v", "all", "-f", "pdf,png", "--press",
         "-n", "ヤン・ヤンセン", "-r", "2", "-d", "2026-09-05", f"--out={out}", "--json"],
        env=support.isolated_env(session_home), cwd=out.parent, timeout=1800)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return {"out": out, "events": support.events(r.stdout), "stderr": r.stderr}


def f(rendered, variant, ext="pdf", press=""):
    return rendered["out"] / f"dan-{variant}-{TAG}{press}.{ext}"


def test_ac13_every_file_written(rendered):
    ev = rendered["events"]
    expected = []
    for v in VARIANTS:
        expected.append(f(rendered, v))
        if v != "proof":
            expected.append(f(rendered, v, press="-CMYK" if "full" in v else "-K"))
        expected.append(f(rendered, v, "png"))
    assert ev[-1] == {"event": "done", "out": str(rendered["out"]),
                      "files": [str(p) for p in expected]}
    progress = [e for e in ev if e["event"] == "progress"]
    assert [p["step"] for p in progress] == list(range(1, 24))
    assert all(p["total"] == 23 for p in progress)
    assert sorted(p.name for p in rendered["out"].iterdir()) == sorted(p.name for p in expected)


def test_ac13_pdfs_are_a3_landscape(rendered):
    pdfinfo = require_program("pdfinfo")
    for p in sorted(rendered["out"].glob("*.pdf")):
        assert p.read_bytes()[:5] == b"%PDF-", p
        info = subprocess.run([pdfinfo, str(p)], capture_output=True, text=True).stdout
        line = next(l for l in info.splitlines() if l.startswith("Page size:"))
        w, h = (float(x) for x in line.split(":")[1].split("pts")[0].split(" x "))
        assert abs(w - A3_PT[0]) < 1 and abs(h - A3_PT[1]) < 1, (p.name, line)
        assert re.search(r"^Pages:\s+1$", info, re.M), (p.name, info)


def test_ac13_pngs_are_a3_at_300_dpi(rendered):
    from PIL import Image
    for v in VARIANTS:
        with Image.open(f(rendered, v, "png")) as im:
            assert abs(im.size[0] - A3_PX_300[0]) <= 1 and abs(im.size[1] - A3_PX_300[1]) <= 1, \
                (v, im.size)


def test_ac13_backgrounds(rendered):
    """overlay: transparent; full-cream: the printed tint."""
    from PIL import Image
    with Image.open(f(rendered, "overlay", "png")) as im:
        assert im.convert("RGBA").getpixel((5, 5))[3] == 0
    with Image.open(f(rendered, "full-cream", "png")) as im:
        r, g, b, a = im.convert("RGBA").getpixel((5, 5))
        assert a == 255 and abs(r - 0xF7) <= 2 and abs(g - 0xF1) <= 2 and abs(b - 0xE3) <= 2


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
    pdftoppm = require_program("pdftoppm")
    empty = {}
    for v in VARIANTS:
        with Image.open(f(rendered, v, "png")) as im:
            if _heading_ink(im, 300) < 100:
                empty[f"{v}.png"] = _heading_ink(im, 300)
        ppm = rendered["out"].parent / f"{v}-page"
        subprocess.run([pdftoppm, "-r", "75", "-png", "-singlefile", str(f(rendered, v)),
                        str(ppm)], check=True)
        with Image.open(str(ppm) + ".png") as im:
            if _heading_ink(im, 75) < 100:
                empty[f"{v}.pdf"] = _heading_ink(im, 75)
    assert not empty, f"no text in the heading column (mm² of ink): {empty}"


def test_ac13_flat_pdf_embeds_yuji_boku(rendered):
    pdffonts = require_program("pdffonts")
    for v in ("overlay-flat", "full-flat", "proof"):
        out = subprocess.run([pdffonts, str(f(rendered, v))], capture_output=True, text=True).stdout
        assert "yuji" in out.lower(), (v, out)


def _inkcov(ghostscript, p):
    r = subprocess.run([ghostscript, "-q", "-o", "-", "-sDEVICE=inkcov", str(p)],
                       capture_output=True, text=True)
    c, m, y, k = (float(x) for x in r.stdout.split()[:4])
    return c, m, y, k


def test_ac13_press_conversions(rendered, ghostscript):
    """The flat -K is greyscale only; -CMYK keeps the coloured border; proof
    gets no press file.  The inked -K is checked separately below."""
    c, m, y, k = _inkcov(ghostscript, f(rendered, "overlay-flat", press="-K"))
    assert c == m == y == 0 and k > 0, ("overlay-flat", c, m, y, k)
    for v in ("full", "full-cream", "full-flat"):
        c, m, y, k = _inkcov(ghostscript, f(rendered, v, press="-CMYK"))
        assert max(c, m, y) > 0, (v, c, m, y, k)
    assert not list(rendered["out"].glob("dan-proof-*-K.pdf"))
    assert not list(rendered["out"].glob("dan-proof-*-CMYK.pdf"))


@pytest.mark.xfail(strict=True, reason=(
    "known, deferred: the inked -K press files are not K-only (cairo's RGB "
    "transparency group survives gs /Gray); see DECISIONS.md, Open, "
    "'The -K press files of the inked variants are not K-only'"))
def test_ac13_press_inked_k_only(rendered, ghostscript):
    c, m, y, k = _inkcov(ghostscript, f(rendered, "overlay", press="-K"))
    assert c == m == y == 0 and k > 0, ("overlay", c, m, y, k)


def test_ac13_inked_svg_carries_its_raster(inkscape, session_home, tmp_path):
    out = tmp_path / "out"
    r = support.run_menkyo(["-c", support.EXAMPLE, "-a", "shihan", "-v", "overlay", "-f", "svg",
                            "-d", "", f"--out={out}"], support.isolated_env(session_home),
                           tmp_path, timeout=900)
    assert r.returncode == 0, r.stderr
    svg = (out / "shihan-overlay-sample.svg").read_text(encoding="utf-8")
    # xlink:href with xlink declared on the root: Inkscape 1.2 ignores a plain
    # href (F-3, see acceptance.md, Agreement).
    assert 'xlink:href="shihan-overlay-sample-textlayer.png"' in svg
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" '
                          'xmlns:xlink="http://www.w3.org/1999/xlink" ')
    from PIL import Image
    with Image.open(out / "shihan-overlay-sample-textlayer.png") as im:
        assert im.mode == "RGBA" and im.size[0] > 1000
