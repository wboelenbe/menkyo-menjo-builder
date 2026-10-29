"""Developer tests for render-without-inkscape: the pieces under the renderer.

The acceptance tests compare whole renders with Inkscape's; these pin what
those rest on: the writer takes exactly the SVG it claims to and refuses the
rest, its numbers are numbers a PDF reader can parse, the PNG module
round-trips its own files and hands anything else to Pillow, and banding the
raster changes nothing visible.
"""

import re
import zlib

import pytest
from PIL import Image

import support
from menkyo import build_diploma as bd
from menkyo import png, render

PAGE = ('<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="100mm" height="50mm" viewBox="0 0 100 50">{}</svg>')


def _content(pdf):
    """The page's content stream, decompressed."""
    data = pdf.data
    m = re.search(rb"/Contents (\d+) 0 R", data)
    obj = re.search(rb"\n%s 0 obj\n<<[^>]*/Length (\d+) >>\nstream\n" % m.group(1), data)
    start = obj.end()
    return zlib.decompress(data[start:start + int(obj.group(1))]).decode()


def _pdf(body, **kw):
    return render.svg_to_pdf(PAGE.format(body), **kw)[0]


# ---------------------------------------------------------------- numbers ---
@pytest.mark.parametrize("v, want", [(6.123233995736766e-17, "0"), (-0.0, "0"),
                                     (0.0115, "0.0115"), (196.2, "196.2"),
                                     (-1e-12, "0"), (2.834645669291339, "2.8346456693")])
def test_matrix_numbers_have_no_exponent(v, want):
    assert render._g(v) == want


def test_rotated_text_has_a_plain_matrix():
    """cos 90° is 6e-17; written as such, pdfium drops the whole matrix and
    the rotated ー vanished."""
    text = ('<text x="50" y="25" font-family="Yuji Boku" font-size="10" '
            'fill="#111111" text-anchor="middle" transform="rotate(90 50 21)">ー</text>')
    content = _content(_pdf(text))
    assert not re.search(r"\de-?\d", content), content[:200]
    assert "0 1 -1 0 71 -29 cm" in content


# -------------------------------------------------------------- path data ---
def test_path_commands_absolute_and_relative():
    ops = render.path_ops("M 1 2 l 3 0 h 1 V 5 c 1 1 2 2 3 3 s 1 1 2 2 "
                          "q 1 1 2 0 t 2 0 Z")
    assert ops[0] == "1 2 m" and ops[1] == "4 2 l" and ops[2] == "5 2 l"
    assert ops[3] == "5 5 l" and ops[-1] == "h"
    assert all(o.endswith(" c") for o in ops[4:8])


def test_implicit_lineto_after_moveto():
    assert render.path_ops("m 1 1 2 2 3 3") == ["1 1 m", "3 3 l", "6 6 l"]


@pytest.mark.parametrize("d", ["M 0 0 A 5 5 0 0 1 10 0", "M 0 0 a 5 5 0 0 1 10 0"])
def test_arcs_are_refused(d):
    with pytest.raises(SystemExit, match="arc"):
        render.path_ops(d)


@pytest.mark.parametrize("d", ["0 0 L 1 1", "M 0", "M 0 0 Z 3 4", "M 0 0 # 1"])
def test_bad_path_data_is_refused(d):
    with pytest.raises(SystemExit, match="path data"):
        render.path_ops(d)


# ----------------------------------------------------------- refusing SVG ---
@pytest.mark.parametrize("body, word", [
    ('<ellipse cx="1" cy="1" rx="1" ry="1"/>', "<ellipse>"),
    ('<use href="#x"/>', "<use>"),
    ('<rect x="1" y="1" width="1" height="1" style="fill:red"/>', "style"),
    ('<rect x="1" y="1" width="1" height="1" rx="1"/>', "rx"),
    ('<g opacity="0.5"/>', "opacity"),
    ('<g transform="skewX(10)"/>', "skewX"),
    ('<path d="M0 0 L1 1" fill="red"/>', "colour"),
    ('<path d="M0 0 L1 1" fill-rule="inherit"/>', "fill-rule"),
    ('<text x="1" y="1" font-size="5" font-family="Arial">a</text>', "Arial"),
    ('<text x="1" y="1" font-size="5" text-anchor="justify">a</text>', "text-anchor"),
    ('<text x="1" y="1" font-size="5"><tspan>a</tspan></text>', "inside <text>"),
])
def test_what_the_writer_does_not_handle_is_refused(body, word):
    with pytest.raises(SystemExit) as e:
        _pdf(body)
    assert word in str(e.value.code), e.value.code


def test_the_whole_document_is_accepted():
    """Every element and attribute document() writes, in every variant."""
    for kw in ({}, {"guides": True}, {"layer": "chrome"}, {"layer": "text"}):
        render.svg_to_pdf(bd.document("右授与ス", "段位免状", name="ヤン", rank="二段",
                                      date=bd.date_column("2024-07-01"), **kw))


# ---------------------------------------------------------------- colours ---
def test_neutral_colours_are_grey_and_others_rgb():
    pdf = _pdf('<rect x="1" y="1" width="5" height="5" fill="#111111"/>'
               '<circle cx="9" cy="9" r="2" fill="none" stroke="#e4b9b9"/>')
    content = _content(pdf)
    assert "0.0667 g" in content and re.search(r"0\.8941 0\.7255 0\.7255 RG", content)
    assert pdf.coloured
    assert not _pdf('<rect x="1" y="1" width="5" height="5" fill="#111"/>').coloured


def test_ink_paints_everything_one_colour():
    content = _content(_pdf('<path d="M0 0 L5 5 Z" fill="#d8c9a8" stroke="#cddbe8"/>',
                            ink="#000000"))
    assert "0 g" in content and "0 G" in content and "rg" not in content


def test_text_box_is_the_outline_box():
    pdf, box = render.svg_to_pdf(PAGE.format(
        '<text x="50" y="30" font-family="Yuji Boku" font-size="10" '
        'text-anchor="middle">右</text>'), area="text")
    x, y, w, h = box
    assert 44 < x < 50 < x + w < 56 and 20 < y < 30 and 5 < h < 11
    assert re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", pdf.data)
    assert abs(pdf.size_pt[0] - w * 72 / 25.4) < 1e-9


def test_no_text_no_box():
    assert render.svg_to_pdf(PAGE.format(""), area="text") == (None, None)


def test_same_input_same_bytes():
    svg = bd.document("右授与ス", "段位免状", name="ヤン")
    assert render.svg_to_pdf(svg)[0].data == render.svg_to_pdf(svg)[0].data


# ------------------------------------------------------------------ fonts ---
def test_the_writer_never_draws_notdef():
    with pytest.raises(SystemExit) as e:
        _pdf('<text x="1" y="1" font-family="Yuji Boku" font-size="5">𠮷</text>')
    msg = str(e.value.code)
    assert "U+20BB7" in msg and "Replace" in msg


def test_missing_font_file_is_named(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "FONT_DIR", str(tmp_path))
    monkeypatch.setattr(render, "_FACES", {})
    with pytest.raises(SystemExit, match=re.escape(str(tmp_path / "YujiBoku-Regular.ttf"))):
        render.open_fonts()


def test_truncated_font_file_is_named(tmp_path, monkeypatch):
    for f in ("YujiBoku-Regular.ttf", "NotoSerifJP-SemiBold.otf"):
        data = open(f"{render.FONT_DIR}/{f}", "rb").read()
        (tmp_path / f).write_bytes(data[:len(data) // 2] if f.endswith(".otf") else data)
    monkeypatch.setattr(render, "FONT_DIR", str(tmp_path))
    monkeypatch.setattr(render, "_FACES", {})
    with pytest.raises(SystemExit, match="NotoSerifJP-SemiBold.otf.*corrupt.*past the end"):
        render.open_fonts()


# -------------------------------------------------------------------- png ---
def _rows(w, h, bpp, seed=0):
    return [bytes((x * 7 + y * 13 + seed) % 256 for x in range(w * bpp)) for y in range(h)]


@pytest.mark.parametrize("mode, bpp", [("LA", 2), ("RGBA", 4)])
def test_png_round_trip(tmp_path, mode, bpp, monkeypatch):
    monkeypatch.setattr(png, "BAND_BYTES", 64)          # many bands and chunks
    rows = _rows(37, 23, bpp)
    p = png.write(str(tmp_path / "a.png"), (37, 23), mode, [rows[:5], rows[5:]], dpi=150)
    with Image.open(p) as im:
        assert im.mode == mode and im.size == (37, 23)
        assert im.tobytes() == b"".join(rows)
        assert all(abs(d - 150) < 0.05 for d in im.info["dpi"])
    assert [r for band in png.bands(p) for r in band] == rows
    assert png.alpha(p).tobytes() == b"".join(r[bpp - 1::bpp] for r in rows)


def test_png_from_another_writer_goes_through_pillow(tmp_path):
    """Pillow filters its rows; png cannot stream that and says so, and
    alpha() reads it through Pillow instead."""
    im = Image.frombytes("RGBA", (40, 30), b"".join(_rows(40, 30, 4, seed=3)))
    p = tmp_path / "pillow.png"
    im.save(p)
    with pytest.raises(png.NotStreamable):
        list(png.bands(str(p)))
    assert png.alpha(str(p)).tobytes() == im.getchannel("A").tobytes()
    grey = tmp_path / "grey.png"
    Image.new("L", (5, 5), 9).save(grey)
    assert png.alpha(str(grey)).tobytes() == b"\xff" * 25


# ----------------------------------------------------------------- raster ---
def test_grey_alpha_is_the_ink_over_white():
    lut = render._grey_alpha(0x11)
    assert lut[255] == 0 and lut[0x11] == 255 and lut[0] == 255
    for v in (40, 128, 200):
        a = lut[v] / 255
        assert abs(255 - a * (255 - 0x11) - v) <= 0.6


def test_banding_changes_nothing_visible(monkeypatch):
    svg = bd.document("右授与ス", "段位免状", guides=True)
    pdf = render.svg_to_pdf(svg)[0]
    size = (round(pdf.size_pt[0] * 50 / 72), round(pdf.size_pt[1] * 50 / 72))
    got = {}
    for colour in (False, True):
        for band in (2 ** 12, 2 ** 30):
            monkeypatch.setattr(render, "BAND_BYTES", band)
            got[colour, band] = b"".join(r for b in render._bands(pdf, size, colour) for r in b)
    for colour in (False, True):
        a, b = got[colour, 2 ** 12], got[colour, 2 ** 30]
        assert len(a) == len(b)
        worst = max(abs(x - y) for i, (x, y) in enumerate(zip(a, b))
                    if not colour or i % 4 == 3)
        assert worst <= 2, (colour, worst)


# ---------------------------------------------------------------- --dpi -----
@pytest.mark.parametrize("dpi", ["0", "-5", "2401"])
def test_dpi_out_of_range_is_a_message(dpi, tmp_path):
    """Not a ZeroDivisionError from the band size, nor a struct.error from
    the PNG header: a message, before anything is written."""
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        bd.main(["-c", str(support.EXAMPLE), "-a", "dan", "-v", "overlay-flat",
                 "-f", "png", f"--dpi={dpi}", f"--out={out}"])
    assert e.value.code == f"--dpi {dpi}: use a resolution from 1 to 2400"
    assert not out.exists()
