"""paper-format: A4 as well as A3, chosen by --paper or by the configuration;
every output name carries the size.

Contract: docs/work/paper-format/acceptance.md.  A4 is the A3 layout scaled
by 1/sqrt(2) on a 297 x 210 mm sheet (the user's decision 1), so most of what
is checked here compares an A4 run with the same run at A3.  AC-7 and AC-18
are also tests/regression/test_golden.py, which compares the goldens through
golden_lib.sized().

Every run passes -c with the shipped example or a configuration written
here, and HOME / XDG_CONFIG_HOME are isolated (conftest, support).
"""

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import support
from menkyo import build_diploma as bd
from menkyo import config as config_mod

EX = str(support.EXAMPLE)
S = 1 / math.sqrt(2)
AWARDS = ["dan", "shihan", "renshi"]
PLAIN = ["overlay", "overlay-flat", "proof"]

# OQ-1: where the dōjō's default lives.  `paper = "a4"` at the top level
# cannot sit beside the existing [paper] table, so the recommendation is a
# key inside it.  Change it here if the user decides otherwise.
SIZE_TABLE, SIZE_KEY = "paper", "size"

A4_PT = (297 * 72 / 25.4, 210 * 72 / 25.4)      # 841.89 x 595.28
A3_PT = (420 * 72 / 25.4, 297 * 72 / 25.4)      # 1190.55 x 841.89

KIT = support.TESTS / "acceptance" / "render_without_inkscape"


# ----------------------------------------------------------------- helpers ----
def _example():
    return support.EXAMPLE.read_text(encoding="utf-8")


def config_with_size(tmp_path, value, name="paper.toml", text=None):
    """The example with `size = <value>` (a TOML literal) under [paper]."""
    text = text if text is not None else _example()
    # the example may already set it (OQ-5): one key, the one asked for
    text = re.sub(rf"^{SIZE_KEY}\s*=.*\n", "", text, flags=re.M)
    head = f"[{SIZE_TABLE}]\n"
    assert head in text
    p = tmp_path / name
    p.write_text(text.replace(head, f"{head}{SIZE_KEY} = {value}\n", 1), encoding="utf-8")
    return str(p)


def run(args, home, tmp_path, exe=None, **env):
    return support.run_menkyo([str(a) for a in args], support.isolated_env(home, **env),
                              tmp_path, exe=exe)


def listing(args, home, tmp_path, config=EX):
    r = run(["-c", config, "--list", *args], home, tmp_path)
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def help_text(home, tmp_path, exe=None, config=EX):
    r = run(["-c", config, "--help"], home, tmp_path, exe=exe, COLUMNS="1000")
    assert r.returncode == 0, r.stderr
    return r.stdout


def render(args, home, tmp_path, out_name="out", config=EX):
    """A --json run into tmp_path/out_name; (events, out dir)."""
    out = tmp_path / out_name
    r = run(["-c", config, *args, f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    ev = support.events(r.stdout)
    assert ev[-1]["event"] == "done"
    return ev, out


def page_size_pt(pdf):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return tuple(doc[0].get_size())
    finally:
        doc.close()


def only(out, pattern):
    found = sorted(p for p in Path(out).glob(pattern) if not p.name.endswith("-textlayer.png"))
    assert len(found) == 1, (pattern, sorted(p.name for p in Path(out).iterdir()))
    return found[0]


def alpha(path):
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        return np.asarray(im.getchannel("A")).astype(float), im.info.get("dpi"), im.size


def _tree(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


# ------------------------------------------------------------------ AC-1 ----
def test_ac1_help_lists_paper(home, tmp_path):
    text = help_text(home, tmp_path)
    m = re.search(r"^\s+--paper\b.*?(?=^\s+-|\Z)", text, re.M | re.S)
    assert m, "--paper is not in --help"
    entry = m.group(0)
    assert "a3" in entry and "a4" in entry, entry
    assert re.search(r"default[^)]*a3|a3[^.]*default", entry, re.I), entry
    assert "config" in entry.lower(), "the help should say the configuration can set it"
    assert "for plain white A3, for every award" not in text


# ------------------------------------------------------------------ AC-2 ----
def test_ac2_default_is_a3(home, tmp_path):
    assert listing(["-a", "dan"], home, tmp_path) == ["dan-overlay-a3-sample.pdf"]
    assert listing(["-a", "dan", "--paper", "a3"], home, tmp_path) == \
        ["dan-overlay-a3-sample.pdf"]


@pytest.mark.render
def test_ac2_explicit_a3_is_the_default_bytes(home, tmp_path):
    common = ["-a", "dan", "-v", ",".join(PLAIN), "-f", "pdf,png,svg", "--dpi", "50",
              "-d", "2026-09-05"]
    _, a = render(common, home, tmp_path, "default")
    _, b = render(common + ["--paper=a3"], home, tmp_path, "explicit")
    ta, tb = _tree(a), _tree(b)
    assert ta and ta.keys() == tb.keys()
    assert all("-a3-" in n for n in ta), sorted(ta)
    assert [n for n in ta if ta[n] != tb[n]] == []
    pdf = a / "dan-overlay-a3-sample.pdf"
    assert page_size_pt(pdf) == pytest.approx(A3_PT, abs=0.01)


# ------------------------------------------------------------------ AC-3 ----
def test_ac3_config_sets_the_default(home, tmp_path):
    cfg = config_with_size(tmp_path, '"a4"')
    assert listing(["-a", "dan"], home, tmp_path, config=cfg) == ["dan-overlay-a4-sample.pdf"]


def test_ac3_flag_beats_config(home, tmp_path):
    a4 = config_with_size(tmp_path, '"a4"', "a4.toml")
    a3 = config_with_size(tmp_path, '"a3"', "a3.toml")
    assert listing(["-a", "dan", "--paper", "a3"], home, tmp_path, config=a4) == \
        ["dan-overlay-a3-sample.pdf"]
    assert listing(["-a", "dan", "--paper=a4"], home, tmp_path, config=a3) == \
        ["dan-overlay-a4-sample.pdf"]
    assert listing(["-a", "dan"], home, tmp_path, config=a3) == ["dan-overlay-a3-sample.pdf"]


def test_ac3_missing_key_is_a3(home, tmp_path):
    minimal = tmp_path / "minimal.toml"
    minimal.write_text('schema = 1\n[[awards]]\nslug = "dan"\nheading = "段位免状"\n'
                       'formula = "右授与ス"\n', encoding="utf-8")
    assert listing([], home, tmp_path, config=str(minimal)) == ["dan-overlay-a3.pdf"]


def test_ac3_save_round_trip(home, tmp_path):
    cfg = config_mod.load(config_with_size(tmp_path, '"a4"'))
    saved = tmp_path / "saved" / "dojo.toml"
    config_mod.save(cfg, str(saved))
    text = saved.read_text(encoding="utf-8")
    assert re.search(rf'^{SIZE_KEY} = "a4"$', text, re.M), text
    assert listing(["-a", "dan"], home, tmp_path, config=str(saved)) == ["dan-overlay-a4.pdf"]
    # and an A3 one says so
    config_mod.save(config_mod.load(EX), str(saved))
    assert re.search(rf'^{SIZE_KEY} = "a3"$', saved.read_text(encoding="utf-8"), re.M)


# OQ-2 (Agreement): upper case is accepted, flag and configuration alike;
# the name says `a4`.
def test_ac3_upper_case_accepted(home, tmp_path):
    assert listing(["-a", "dan", "--paper", "A4"], home, tmp_path) == \
        ["dan-overlay-a4-sample.pdf"]
    cfg = config_with_size(tmp_path, '"A4"')
    assert listing(["-a", "dan"], home, tmp_path, config=cfg) == ["dan-overlay-a4-sample.pdf"]


# ------------------------------------------------------------------ AC-4 ----
BAD_FLAGS = [["--paper", "a5"], ["--paper", "letter"], ["--paper", ""],
             ["--paper", "a3,a4"], ["--paper=a5"]]
BAD_IDS = ["a5", "letter", "empty", "both", "equals-a5"]


@pytest.mark.parametrize("flag", BAD_FLAGS, ids=BAD_IDS)
@pytest.mark.parametrize("listing_only", [False, True], ids=["run", "list"])
def test_ac4_bad_paper_flag(flag, listing_only, home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-f", "svg", "-d", "",
             *(["--list"] if listing_only else []), *flag, f"--out={out}"], home, tmp_path)
    assert r.returncode != 0
    assert r.stdout == ""
    assert "--paper" in r.stderr and "a3" in r.stderr and "a4" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr
    assert not out.exists()


@pytest.mark.parametrize("flag", BAD_FLAGS, ids=BAD_IDS)
def test_ac4_bad_paper_flag_json(flag, home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan", "-v", "overlay-flat", "-d", "", *flag,
             f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert len(ev) == 1 and ev[0]["event"] == "error", ev
    assert "--paper" in ev[0]["message"]
    assert not out.exists()


def test_ac4_missing_value(home, tmp_path):
    r = run(["-c", EX, "--list", "--paper"], home, tmp_path)
    assert r.returncode != 0 and r.stdout == ""
    assert "--paper" in r.stderr and "Traceback" not in r.stderr
    r = run(["-c", EX, "--list", "--json", "--paper"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert [e["event"] for e in ev] == ["error"] and "--paper" in ev[0]["message"]


def test_ac4_bad_flag_cleans_nothing(home, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "earlier.pdf").write_bytes(b"%PDF-1.4 an earlier certificate")
    r = run(["-c", EX, "-a", "dan", "--clean", "--paper", "b4", f"--out={out}"],
            home, tmp_path)
    assert r.returncode != 0
    assert sorted(os.listdir(out)) == ["earlier.pdf"]


# ------------------------------------------------------------------ AC-5 ----
BAD_VALUES = ['"a5"', "4", '""', "true"]


def _assert_config_message(text, cfg):
    assert cfg in text, text
    assert f"[{SIZE_TABLE}]" in text and SIZE_KEY in text, text
    assert "a3" in text and "a4" in text, text
    assert "Traceback" not in text


@pytest.mark.parametrize("value", BAD_VALUES)
@pytest.mark.parametrize("extra", [[], ["--list"], ["--paper", "a3"]],
                         ids=["run", "list", "with-flag"])
def test_ac5_bad_config_value(value, extra, home, tmp_path):
    cfg = config_with_size(tmp_path, value)
    out = tmp_path / "out"
    r = run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-f", "svg", "-d", "", *extra,
             f"--out={out}"], home, tmp_path)
    assert r.returncode == 1, (r.returncode, r.stderr)
    assert r.stdout == ""
    _assert_config_message(r.stderr, cfg)
    assert not out.exists()


@pytest.mark.parametrize("value", BAD_VALUES)
def test_ac5_bad_config_value_json(value, home, tmp_path):
    cfg = config_with_size(tmp_path, value)
    out = tmp_path / "out"
    r = run(["-c", cfg, "-a", "dan", "-d", "", f"--out={out}", "--json"], home, tmp_path)
    assert r.returncode == 1
    ev = support.events(r.stdout)
    assert len(ev) == 1 and ev[0]["event"] == "error", ev
    _assert_config_message(ev[0]["message"], cfg)
    assert not out.exists()


# ------------------------------------------------------------------ AC-6 ----
NAME_CASES = [
    ([], ["dan-overlay-a3-sample.pdf"]),
    (["--paper", "a4"], ["dan-overlay-a4-sample.pdf"]),
    (["-v", "overlay-flat"], ["dan-overlay-flat-a3-sample.pdf"]),
    (["-v", "proof", "--paper", "a4"], ["dan-proof-a4-sample.pdf"]),
    (["-n", "ヤン・ヤンセン", "-r", "2"], ["dan-overlay-a3-2-ヤン-ヤンセン.pdf"]),
    (["-n", "ヤン・ヤンセン", "-r", "2", "--paper", "a4"],
     ["dan-overlay-a4-2-ヤン-ヤンセン.pdf"]),
    (["--suffix", ""], ["dan-overlay-a3.pdf"]),
    (["--suffix", "archive", "-n", "ヤン・ヤンセン"], ["dan-overlay-a3-archive.pdf"]),
    (["-v", "overlay,overlay-flat,proof", "-f", "pdf,png,svg", "--paper", "a4"],
     [f"dan-{v}-a4-sample.{e}" for v in PLAIN for e in ("pdf", "png", "svg")]),
]


@pytest.mark.parametrize("args,names", NAME_CASES,
                         ids=["default", "a4", "flat", "proof-a4", "name-rank",
                              "name-rank-a4", "no-suffix", "suffix", "every-format"])
def test_ac6_list_names(args, names, home, tmp_path):
    assert listing(["-a", "dan", *args], home, tmp_path) == names


def test_ac6_planned_events(home, tmp_path):
    r = run(["-c", EX, "--list", "--json", "--all", "--paper", "a4"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    ev = support.events(r.stdout)
    assert ev == [{"event": "planned", "file": f"{a}-{v}-a4-sample.pdf"}
                  for a in AWARDS for v in PLAIN]


@pytest.mark.render
def test_ac6_written_names_and_events(home, tmp_path):
    ev, out = render(["-a", "dan", "-v", "overlay", "-f", "pdf,svg", "--paper", "a4",
                      "-d", "2026-09-05"], home, tmp_path)
    stem = "dan-overlay-a4-sample"
    files = [e["path"] for e in ev if e["event"] == "file"]
    assert files == [str(out / f"{stem}.pdf"), str(out / f"{stem}.svg"),
                     str(out / f"{stem}-textlayer.png")]
    assert ev[-1] == {"event": "done", "out": str(out), "files": files}
    assert sorted(os.listdir(out)) == sorted(Path(f).name for f in files)
    svg = (out / f"{stem}.svg").read_text(encoding="utf-8")
    assert f'xlink:href="{stem}-textlayer.png"' in svg

    # and the plain stdout says the same
    r = run(["-c", EX, "-a", "dan", "-v", "overlay-flat", "--paper", "a4", "-d", "",
             f"--out={tmp_path / 'plain'}"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0] == \
        f"wrote {tmp_path / 'plain' / 'dan-overlay-flat-a4-sample.pdf'}"


# ------------------------------------------------------------------ AC-7 ----
def test_ac7_sized_name_mapping():
    """The regression's mapping inserts the size after the variant, and only
    there."""
    sys.path.insert(0, str(support.TESTS / "regression"))
    from golden_lib import sized
    assert sized("dan-overlay-sample.pdf", "a3") == "dan-overlay-a3-sample.pdf"
    assert sized("dan-overlay-flat-sample.svg", "a3") == "dan-overlay-flat-a3-sample.svg"
    assert sized("kyoshi-proof.png", "a3") == "kyoshi-proof-a3.png"
    assert sized('xlink:href="dan-overlay-textlayer.png"', "a3") == \
        'xlink:href="dan-overlay-a3-textlayer.png"'
    assert sized("wrote <OUT>/dan-overlay-2-ヤン-ヤンセン.pdf\n", "a3") == \
        "wrote <OUT>/dan-overlay-a3-2-ヤン-ヤンセン.pdf\n"
    # idempotent: a name that has its size keeps it (Agreement)
    for name in ("dan-overlay-a3-sample.pdf", "dan-overlay-flat-a4.svg",
                 "dan-proof-a3-sample-textlayer.png"):
        assert sized(name, "a3") == name
    once = sized("dan-overlay-sample.pdf\ndan-proof.png\n", "a3")
    assert sized(once, "a3") == once


# ------------------------------------------------------------------ AC-8 ----
@pytest.mark.render
def test_ac8_pdf_page_size(home, tmp_path):
    _, out = render(["-a", "dan", "-v", ",".join(PLAIN), "--paper", "a4", "-d", ""],
                    home, tmp_path)
    for v in PLAIN:
        assert page_size_pt(out / f"dan-{v}-a4-sample.pdf") == \
            pytest.approx(A4_PT, abs=0.01), v
    _, out3 = render(["-a", "dan", "-v", "overlay-flat", "-d", ""], home, tmp_path, "a3")
    assert page_size_pt(out3 / "dan-overlay-flat-a3-sample.pdf") == \
        pytest.approx(A3_PT, abs=0.01)


def test_ac8_svg_root_size(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan", "-v", "overlay-flat,proof", "-f", "svg", "--no-ink",
             "--paper", "a4", "-d", "", f"--out={out}"], home, tmp_path)
    assert r.returncode == 0, r.stderr
    for v in ("overlay-flat", "proof"):
        head = (out / f"dan-{v}-a4-sample.svg").read_text(encoding="utf-8")[:400]
        assert re.search(r'<svg [^>]*width="297(\.0+)?mm" height="210(\.0+)?mm"', head), head


# ------------------------------------------------------------------ AC-9 ----
TRACED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
          '<path d="M 100 100 l 800 0 l 0 800 c -100 50 -700 50 -800 0 z '
          'M 300 300 L 700 300 L 700 700 L 300 700 Z"/></svg>')


def _custom_paper(tmp_path):
    text = (_example().replace("border = 22.0", "border = 12.0")
            .replace("safe_inset = 38.0", "safe_inset = 30.0")
            .replace("text_drop = 0.05", "text_drop = 0.08"))
    p = tmp_path / "custom.toml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def _traced(tmp_path):
    text = _example().replace("traced_glyphs = false", "traced_glyphs = true")
    p = tmp_path / "traced.toml"
    p.write_text(text, encoding="utf-8")
    (tmp_path / "crest").mkdir()
    (tmp_path / "crest" / "〇.svg").write_text(TRACED, encoding="utf-8")
    return str(p)


SCALE_CASES = {
    "filled": (None, ["-a", "dan", "-v", "overlay-flat", "-n", "ヤン・ヤンセン", "-r", "2",
                      "-d", "2026-09-05"], 15),
    "blank": (None, ["-a", "dan", "-v", "overlay-flat", "-n", "", "-r", "", "-d", ""], 15),
    "proof": (None, ["-a", "dan", "-v", "proof", "-n", "", "-r", "", "-d", ""], 15),
    "licence-long-name": (None, ["-a", "shihan", "-v", "overlay-flat",
                                 "-n", "アレクサンドル・ファン・デル・フェルデン",
                                 "-d", "2020-10-20"], 15),
    "inked": (None, ["-a", "dan", "-v", "overlay", "-d", "2026-09-05"], 20),
    "traced-crest": (_traced, ["-a", "dan", "-v", "overlay-flat", "-d", ""], 15),
    "custom-margins": (_custom_paper, ["-a", "dan", "-v", "proof", "-d", ""], 15),
}


def _bbox_mm(a, dpi):
    import numpy as np
    ys, xs = np.nonzero(a > 32)
    k = 25.4 / dpi
    return np.array([xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k])


@pytest.mark.render
@pytest.mark.parametrize("case", list(SCALE_CASES))
def test_ac9_a4_is_a3_scaled(case, home, tmp_path):
    import numpy as np
    from PIL import Image
    make_config, args, limit = SCALE_CASES[case]
    cfg = make_config(tmp_path) if make_config else EX
    dpi = 200
    pages = {}
    for size in ("a3", "a4"):
        _, out = render([*args, "-f", "png", "--dpi", str(dpi), "--paper", size],
                        home, tmp_path, size, config=cfg)
        pages[size] = alpha(only(out, f"*-{size}*.png"))[0]
    a3, a4 = pages["a3"], pages["a4"]
    assert a4.shape == (round(210 / 25.4 * dpi), round(297 / 25.4 * dpi))

    box3, box4 = _bbox_mm(a3, dpi) * S, _bbox_mm(a4, dpi)
    assert np.abs(box3 - box4).max() <= 0.3, (case, box3.round(2), box4.round(2))

    scaled = np.asarray(Image.fromarray(a3.astype(np.uint8)).resize(
        (a4.shape[1], a4.shape[0]), Image.LANCZOS)).astype(float)
    drawn = (a4 > 0) | (scaled > 0)
    diff = float(np.abs(a4 - scaled)[drawn].mean())
    print(f"\n{case}: bbox A3*s {box3.round(2)} A4 {box4.round(2)}, mean |diff| {diff:.2f}")
    assert diff <= limit, (case, diff)


# ----------------------------------------------------------------- AC-10 ----
@pytest.mark.render
@pytest.mark.parametrize("variant", ["overlay-flat", "proof"])
def test_ac10_png_size(variant, home, tmp_path):
    expect = {("a4", 300): (3508, 2480), ("a4", 150): (1754, 1240),
              ("a3", 300): (4961, 3508)}
    dpis = {}
    for (size, dpi), px in expect.items():
        _, out = render(["-a", "renshi", "-v", variant, "-f", "png", "--dpi", str(dpi),
                         "--paper", size, "-d", ""], home, tmp_path, f"{size}-{dpi}")
        _, info, got = alpha(only(out, f"renshi-{variant}-{size}-sample.png"))
        assert got == px, (size, dpi, got)
        dpis[(size, dpi)] = info
    assert dpis[("a4", 300)] == dpis[("a3", 300)]
    assert dpis[("a4", 300)] and round(dpis[("a4", 300)][0]) == 300


def test_ac10_dpi_range_unchanged(home, tmp_path):
    for dpi, ok in (("0", False), ("1", True), ("2400", True), ("2401", False)):
        r = run(["-c", EX, "--list", "--paper", "a4", "--dpi", dpi], home, tmp_path)
        assert (r.returncode == 0) == ok, (dpi, r.stderr)


# ----------------------------------------------------------------- AC-11 ----
@pytest.fixture(scope="module")
def text_layers(session_home, tmp_path_factory):
    """The dan overlay's graded text layer at A3 and at A4, rendered once for
    AC-11 and AC-12 (Agreement)."""
    tmp = tmp_path_factory.mktemp("textlayers")
    layers = {}
    for size in ("a3", "a4"):
        _, out = render(["-a", "dan", "-v", "overlay", "-f", "svg", "--paper", size,
                         "-d", "2026-09-05"], session_home, tmp, size)
        layers[size] = out / f"dan-overlay-{size}-sample-textlayer.png"
    return layers


@pytest.mark.render
def test_ac11_text_layer_600_dpi(text_layers):
    from PIL import Image
    sizes = {}
    for size in ("a3", "a4"):
        with Image.open(text_layers[size]) as im:
            assert im.mode == "RGBA"
            sizes[size] = im.size
    w3, h3 = sizes["a3"]
    w4, h4 = sizes["a4"]
    assert abs(w4 - w3 * S) <= 2 and abs(h4 - h3 * S) <= 2, sizes
    assert bd.INK_DPI == 600.0


# ----------------------------------------------------------------- AC-12 ----
def _ink_stats(path):
    import numpy as np
    from scipy import ndimage
    a = alpha(path)[0]
    inside = ndimage.binary_erosion(a >= 128, iterations=3)
    v = a[inside]
    return float((v < 0.9 * 255).mean()), float(np.percentile(v, 5)), float(v.mean())


@pytest.mark.render
def test_ac12_ink_reads_as_a3(text_layers):
    l3, p3, m3 = _ink_stats(text_layers["a3"])
    l4, p4, m4 = _ink_stats(text_layers["a4"])
    print(f"\nlifted A3 {l3:.4f} A4 {l4:.4f}; p5 {p3} {p4}; mean {m3:.2f} {m4:.2f}")
    assert l4 > 0, "the A4 text is not graded"
    assert 0.60 <= l4 / l3 <= 1.40          # widened in the Agreement
    assert abs(p4 - p3) <= 8
    assert abs(m4 - m3) <= 1.5


# ----------------------------------------------------------------- AC-13 ----
def _peak(args, home, tmp_path, tag):
    report = tmp_path / f"{tag}.json"
    r = subprocess.run([sys.executable, str(KIT / "peak_driver.py"), str(report), "--",
                        "-c", EX, *args, f"--out={tmp_path / tag}"],
                       env=support.isolated_env(home), cwd=str(tmp_path),
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(report.read_text())["peak_rss"] / 2 ** 20


@pytest.mark.render
def test_ac13_a4_peak_memory(home, tmp_path):
    portal = ["-a", "dan", "-v", "overlay", "-f", "pdf", "--name=ヤン・ヤンセン",
              "--rank=二段", "--date=2026-09-05", "--json"]
    a3 = _peak(portal + ["--paper=a3"], home, tmp_path, "a3")
    a4 = _peak(portal + ["--paper=a4"], home, tmp_path, "a4")
    print(f"\npeak RSS A3 {a3:.0f} MB, A4 {a4:.0f} MB ({a4 / a3:.0%})")
    assert a4 <= 0.9 * a3


# ----------------------------------------------------------------- AC-14 ----
@pytest.mark.render
def test_ac14_json_events_same_but_names(home, tmp_path):
    args = ["-a", "dan", "-v", "overlay,proof", "-f", "pdf,png", "--dpi", "50",
            "-n", "ヤン・ヤンセン", "-r", "2", "-d", "2026-09-05"]
    ev3, out3 = render(args + ["--paper", "a3"], home, tmp_path, "x")
    ev4, out4 = render(args + ["--paper", "a4"], home, tmp_path, "y")

    def norm(ev, out, size):
        return json.loads(json.dumps(ev, ensure_ascii=False)
                          .replace(str(out), "<OUT>").replace(f"-{size}-", "-<SIZE>-"))
    assert norm(ev3, out3, "a3") == norm(ev4, out4, "a4")
    files = [e["path"] for e in ev4 if e["event"] == "file"]
    assert files and all("-a4-2-ヤン-ヤンセン." in f for f in files), files


# ----------------------------------------------------------------- AC-15 ----
@pytest.mark.render
def test_ac15_all_variants_a4(home, tmp_path):
    ev, out = render(["--all", "--paper", "a4", "-d", "2026-09-05"], home, tmp_path)
    assert ev[-1]["files"] == [str(out / f"{a}-{v}-a4-sample.pdf")
                               for a in AWARDS for v in PLAIN]
    for f in ev[-1]["files"]:
        assert page_size_pt(f) == pytest.approx(A4_PT, abs=0.01), f


# ----------------------------------------------------------------- AC-16 ----
@pytest.mark.render
def test_ac16_deterministic(home, tmp_path):
    args = ["-a", "dan", "-v", "overlay,overlay-flat", "-f", "pdf,png", "--dpi", "60",
            "--paper", "a4", "-d", "2026-09-05"]
    _, a = render(args, home, tmp_path, "one")
    _, b = render(args, home, tmp_path, "two")
    ta, tb = _tree(a), _tree(b)
    assert len(ta) == 4 and ta == tb


# ----------------------------------------------------------------- AC-17 ----
def test_ac17_glyph_check_first(home, tmp_path):
    out = tmp_path / "out"
    r = run(["-c", EX, "-a", "dan", "--paper", "a4", "--name=𠮷田", "--rank=", "--date=",
             f"--out={out}"], home, tmp_path)
    assert r.returncode == 1
    assert "U+20BB7" in r.stderr and "--name" in r.stderr
    assert not out.exists()


# ----------------------------------------------------------------- AC-19 ----
@pytest.mark.slow
@pytest.mark.render
def test_ac19_installed_wheel_a4(installed, home, tmp_path):
    exe = [str(installed["menkyo"])]
    r = run(["--paper", "a4", "-a", "dan", "-v", "overlay-flat", "-d", "", "--json"],
            home, tmp_path, exe=exe)
    assert r.returncode == 0, r.stdout + r.stderr
    docs = home / "Documents" / "Menkyo"
    target = docs / "dan-overlay-flat-a4-sample.pdf"
    assert support.events(r.stdout)[-1] == {"event": "done", "out": str(docs),
                                            "files": [str(target)]}
    assert page_size_pt(target) == pytest.approx(A4_PT, abs=0.01)

    ex = run(["--example-config"], home, tmp_path, exe=exe)
    cfg = config_with_size(tmp_path, '"a4"', text=ex.stdout)
    r = run(["-c", cfg, "-a", "dan", "-v", "overlay-flat", "-d", "", "--out", "out"],
            home, tmp_path, exe=exe)
    assert r.returncode == 0, r.stderr
    assert page_size_pt(tmp_path / "out" / "dan-overlay-flat-a4-sample.pdf") == \
        pytest.approx(A4_PT, abs=0.01)


# ----------------------------------------------------------------- AC-20 ----
BEFORE_FLAGS = {"--all", "--awards", "--clean", "--config", "--date", "--dpi",
                "--example-config", "--formats", "--help", "--honorific", "--json",
                "--list", "--name", "--no-ink", "--out", "--rank", "--suffix",
                "--variants", "--version"}


def test_ac20_help_flags(home, tmp_path):
    text = help_text(home, tmp_path)
    options = text.split("options:", 1)[1] if "options:" in text else text
    longs = set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", options))
    assert longs == BEFORE_FLAGS | {"--paper"}, longs ^ (BEFORE_FLAGS | {"--paper"})
    shorts = set(re.findall(r"^\s+(-[a-z]),", options, re.M))
    assert shorts == {"-h", "-c", "-a", "-v", "-f", "-n", "-r", "-d", "-o"}, shorts


# ----------------------------------------------------------------- AC-21 ----
def _readme():
    return (support.REPO / "README.md").read_text(encoding="utf-8")


# A name of an output file without a size: <award>-<variant> followed by
# something other than -<size>.  The placeholder spelling counts as a size.
_UNSIZED = re.compile(r"(?:\b(?:dan|shihan|renshi)|<award>|\*)"
                      r"-(?:overlay-flat|overlay(?!-flat)|proof|<variant>)"
                      r"(?!-(?:a3|a4)(?!\w)|-<size>)(?=[-.])")


def test_ac21_readme():
    text = _readme()
    assert re.search(r"^\|\s*`--paper", text, re.M), "no --paper row in Options"
    assert re.search(rf"^\s*{SIZE_KEY}\s*=\s*\"a[34]\"", text, re.M), \
        "the configuration example does not show the paper size"
    assert "<award>-<variant>-<size>" in text
    assert re.search(r"297\s*×\s*210\s*mm", text)
    assert re.search(r"--paper[ =]a4", text)


@pytest.mark.parametrize("path", ["README.md", "src/menkyo/example.toml",
                                  "src/menkyo/build_diploma.py"])
def test_ac21_names_in_docs(path):
    text = (support.REPO / path).read_text(encoding="utf-8")
    if path.endswith(".py"):
        text = bd.__doc__
    lines = [l for l in text.splitlines() if _UNSIZED.search(l)]
    assert not lines, lines[:8]


def test_ac21_example_config():
    import tomllib
    raw = tomllib.loads(_example())
    assert raw[SIZE_TABLE][SIZE_KEY] == "a3"
    section = _example().split(f"[{SIZE_TABLE}]", 1)[1].split("\n[", 1)[0]
    assert "a4" in section and "--paper" in section
    # the margins are A3 millimetres that scale on A4 (Agreement)
    assert "Millimetres, on plain white A3." not in section
    assert re.search(r"scale", section, re.I), section


def test_ac21_decisions():
    text = (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")
    body, open_ = text.split("\n## Open\n", 1)
    assert "Paper format: A4 as well as A3" not in open_
    assert "A4 as well as A3" not in open_
    entries = re.split(r"^(?=## )", body, flags=re.M)
    sys.path.insert(0, str(support.TESTS / "acceptance"))
    import house_style as hs
    new = [e for e in entries[hs.PINNED_BLOCKS:] if "A4" in e.splitlines()[0]]
    assert len(new) == 1, [e.splitlines()[0] for e in entries[hs.PINNED_BLOCKS:]]
    entry = new[0]
    assert re.match(r"## \d{4}-\d{2}-\d{2} – ", entry)
    for needle in ("--paper", SIZE_KEY, "297 × 210", "-a4", "600 dpi",
                   "Plain white paper only"):
        assert needle in entry, needle
