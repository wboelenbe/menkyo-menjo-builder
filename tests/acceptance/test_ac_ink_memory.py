"""ink-memory: ink.ink_layer uses much less memory and grades the same.

Contract: docs/work/ink-memory/acceptance.md.  The yardstick throughout is
tests/acceptance/ink_memory/reference_ink.py, a pinned copy of ink.py as at
823af58, and the graded alpha it stored for a fixed input:

    ink_memory/textlayer-crop.png              Inkscape's C-1 text layer (the
                                               example config), 600 dpi, cropped
                                               to 1999 x 1500 at (5300, 0)
    ink_memory/textlayer-crop-inked-alpha.png  823af58's graded alpha for it

The memory tests tile that crop up to C-1's real text-layer size, 7299 x 3733,
and run each implementation in a fresh subprocess, so the peaks are comparable
on whatever machine runs them.
"""

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import support
from menkyo import ink

HERE = Path(__file__).resolve().parent / "ink_memory"
CROP = HERE / "textlayer-crop.png"
CROP_ALPHA = HERE / "textlayer-crop-inked-alpha.png"
REFERENCE = HERE / "reference_ink.py"
DRIVER = HERE / "ink_driver.py"

INK_RGB = (17, 17, 17)            # build_diploma.INK, "#111111"
C1_SIZE = (7299, 3733)            # C-1's text layer at 600 dpi, Inkscape 1.2
MEMORY_RATIO = 0.40               # AC-2
TIME_RATIO = 2.0                  # AC-12 guard; the target (1.25) is reported
C1 = ["-a", "dan", "-v", "overlay", "-n", "ヤン・ヤンセン", "-r", "2",
      "-d", "2024-07-01"]

Image.MAX_IMAGE_PIXELS = None


def _reference():
    spec = importlib.util.spec_from_file_location("reference_ink", REFERENCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rgba(path):
    return np.array(Image.open(path).convert("RGBA"))


def _both(tmp_path, src, dpi=600.0, **kw):
    """Grade `src` with the current and the reference ink_layer; both RGBA."""
    cur, ref = tmp_path / "current.png", tmp_path / "reference.png"
    assert ink.ink_layer(str(src), str(cur), dpi, **kw) == str(cur)
    _reference().ink_layer(str(src), str(ref), dpi, **kw)
    return _rgba(cur), _rgba(ref)


def _max_alpha_diff(a, b):
    return int(np.abs(a[..., 3].astype(int) - b[..., 3].astype(int)).max())


def _composite_white(rgba):
    a = rgba[..., 3].astype(float) / 255.0
    return 255.0 - a * (255.0 - rgba[..., 0].astype(float))


def _check_colour(out, src):
    """AC-5: where the output has ink, RGB is grey and either the renderer's
    own value at that pixel or the ink colour."""
    inked = out[..., 3] > 0
    rgb, src_rgb = out[..., :3][inked], src[..., :3][inked]
    assert (rgb[:, 0] == rgb[:, 1]).all() and (rgb[:, 1] == rgb[:, 2]).all()
    ok = (rgb == src_rgb).all(axis=1) | (rgb == np.array(INK_RGB)).all(axis=1)
    assert ok.all(), f"{int((~ok).sum())} inked pixels with another colour"


# ------------------------------------------------------------ fixtures ----
def _tile(src, size, dst):
    im = Image.open(src).convert("RGBA")
    big = Image.new("RGBA", size, (255, 255, 255, 0))
    for y in range(0, size[1], im.height):
        for x in range(0, size[0], im.width):
            big.paste(im, (x, y))
    big.save(dst)
    return dst


@pytest.fixture(scope="module")
def c1_sized(tmp_path_factory):
    """The crop tiled to C-1's text-layer size: a 27 Mpx RGBA PNG."""
    return _tile(CROP, C1_SIZE, tmp_path_factory.mktemp("ink-c1") / "c1-sized.png")


_MEASURE = textwrap.dedent("""
    import importlib.util, json, resource, sys, time
    import numpy, scipy.ndimage, PIL.Image, PIL.ImageChops  # imports before the baseline
    which, src, dst, ref = sys.argv[1:5]
    if which == "reference":
        spec = importlib.util.spec_from_file_location("reference_ink", ref)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    else:
        from menkyo import ink as mod
    PIL.Image.MAX_IMAGE_PIXELS = None
    def peak():
        # VmHWM on Linux: ru_maxrss survives exec there, and a vfork-spawned
        # child would start at pytest's peak (see ink_driver._peak_bytes).
        if sys.platform.startswith("linux"):
            for line in open("/proc/self/status"):
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) * 1024
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r if sys.platform == "darwin" else r * 1024
    base = peak(); t = time.perf_counter()
    mod.ink_layer(src, dst, 600.0)
    print(json.dumps({"base": base, "peak": peak(), "delta": peak() - base,
                      "seconds": time.perf_counter() - t}))
""")


def _measure(which, src, dst, home):
    r = subprocess.run(
        [sys.executable, "-c", _MEASURE, which, str(src), str(dst), str(REFERENCE)],
        env=support.isolated_env(home), capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def measured(c1_sized, session_home, tmp_path_factory):
    """Each implementation once, in its own fresh process, on the C-1-sized input."""
    out = tmp_path_factory.mktemp("ink-measured")
    res = {}
    for which in ("reference", "current"):
        dst = out / f"{which}.png"
        res[which] = _measure(which, c1_sized, dst, session_home)
        res[which]["png"] = dst
    print("\nink_layer on 7299x3733: "
          + "; ".join(f"{k} peak +{v['delta'] / 1e6:.0f} MB in {v['seconds']:.2f} s"
                      for k, v in res.items()))
    return res


# ---------------------------------------------------------------- AC-2 ----
def test_ac2_ink_layer_peak_memory(measured):
    cur, ref = measured["current"]["delta"], measured["reference"]["delta"]
    assert ref > 0
    assert cur <= MEMORY_RATIO * ref, (
        f"ink_layer peak +{cur / 1e6:.0f} MB, reference +{ref / 1e6:.0f} MB: "
        f"ratio {cur / ref:.2f} > {MEMORY_RATIO}")


# ---------------------------------------------------------------- AC-3 ----
def test_ac3_alpha_matches_stored_reference(tmp_path):
    out = tmp_path / "out.png"
    ink.ink_layer(str(CROP), str(out), 600.0)
    got = _rgba(out)[..., 3].astype(int)
    want = np.array(Image.open(CROP_ALPHA)).astype(int)
    assert got.shape == want.shape
    assert np.abs(got - want).max() <= 1


def test_ac3_alpha_matches_reference_at_c1_size(measured):
    cur, ref = _rgba(measured["current"]["png"]), _rgba(measured["reference"]["png"])
    assert cur.shape == ref.shape
    assert _max_alpha_diff(cur, ref) <= 1


@pytest.mark.parametrize("seed", [0, 5, 11])
def test_ac3_alpha_matches_reference_other_seeds(tmp_path, seed):
    cur, ref = _both(tmp_path, CROP, seed=seed)
    assert _max_alpha_diff(cur, ref) <= 1


@pytest.mark.parametrize("dpi,factor", [(300.0, 2), (150.0, 4)])
def test_ac3_alpha_matches_reference_other_dpi(tmp_path, dpi, factor):
    """300 dpi still works on a reduced field; 150 dpi is below WORK_DPI, where
    the field is computed at full size (scale 1)."""
    im = Image.open(CROP)
    small = tmp_path / "small.png"
    im.resize((im.width // factor, im.height // factor), Image.LANCZOS).save(small)
    cur, ref = _both(tmp_path, small, dpi=dpi)
    assert _max_alpha_diff(cur, ref) <= 1


# ---------------------------------------------------------------- AC-4 ----
def test_ac4_transparent_stays_transparent(tmp_path):
    out = tmp_path / "out.png"
    ink.ink_layer(str(CROP), str(out), 600.0)
    src, got = _rgba(CROP), _rgba(out)
    assert (got[..., 3][src[..., 3] == 0] == 0).all()


def test_ac4_transparent_stays_transparent_at_c1_size(c1_sized, measured):
    src, got = _rgba(c1_sized), _rgba(measured["current"]["png"])
    assert (got[..., 3][src[..., 3] == 0] == 0).all()


# ---------------------------------------------------------------- AC-5 ----
def test_ac5_colour_is_the_ink(tmp_path):
    cur, ref = _both(tmp_path, CROP)
    _check_colour(cur, _rgba(CROP))
    diff = np.abs(_composite_white(cur) - _composite_white(ref))
    assert diff.max() <= 2.0, f"over white: max {diff.max():.3f}/255"


def test_ac5_colour_is_the_ink_at_c1_size(c1_sized, measured):
    cur, ref = _rgba(measured["current"]["png"]), _rgba(measured["reference"]["png"])
    _check_colour(cur, _rgba(c1_sized))
    diff = np.abs(_composite_white(cur) - _composite_white(ref))
    assert diff.max() <= 2.0, f"over white: max {diff.max():.3f}/255"


# ---------------------------------------------------------------- AC-6 ----
def test_ac6_png_format(tmp_path):
    out = tmp_path / "out.png"
    assert ink.ink_layer(str(CROP), str(out), 600.0) == str(out)
    with Image.open(out) as im, Image.open(CROP) as src:
        assert im.format == "PNG"
        assert im.mode == "RGBA"
        assert im.size == src.size


def test_ac6_in_place(tmp_path):
    """_inked_text_image grades the raster in place: same path in and out."""
    p = tmp_path / "layer.png"
    p.write_bytes(CROP.read_bytes())
    assert ink.ink_layer(str(p), str(p), 600.0) == str(p)
    got = _rgba(p)[..., 3].astype(int)
    want = np.array(Image.open(CROP_ALPHA)).astype(int)
    assert np.abs(got - want).max() <= 1


# ---------------------------------------------------------------- AC-7 ----
def test_ac7_deterministic(tmp_path, session_home):
    a, b, c = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "c.png"
    ink.ink_layer(str(CROP), str(a), 600.0)
    ink.ink_layer(str(CROP), str(b), 600.0)
    _measure("current", CROP, c, session_home)          # another process
    assert a.read_bytes() == b.read_bytes() == c.read_bytes()


# ---------------------------------------------------------------- AC-8 ----
def _blank(path, mode, alpha):
    """A 300 x 200 raster with nothing above half coverage, in `mode`."""
    im = Image.new("RGBA", (300, 200), (17, 17, 17, alpha))
    if mode == "LA":
        im = im.convert("LA")
    elif mode == "P":
        # every pixel is palette entry 1, the ink, at `alpha` (a tRNS chunk)
        im = Image.new("P", (300, 200), 1)
        im.putpalette([255, 255, 255, 17, 17, 17])
        im.save(path, transparency=bytes([0, alpha]))
        return path
    im.save(path)
    return path


@pytest.mark.parametrize("in_place", [False, True], ids=["separate", "in-place"])
@pytest.mark.parametrize("mode", ["RGBA", "LA", "P"])
@pytest.mark.parametrize("alpha", [0, 100, 127])
def test_ac8_nothing_to_grade(tmp_path, alpha, mode, in_place):
    """No pixel above half coverage: the raster comes back as it went in, as
    RGBA. In place is what _inked_text_image does, e.g. with a blank text
    layer (review R-4)."""
    src = _blank(tmp_path / "blank.png", mode, alpha)
    want = _rgba(src)
    assert want[..., 3].max() == alpha
    out = src if in_place else tmp_path / "out.png"
    assert ink.ink_layer(str(src), str(out), 600.0) == str(out)
    with Image.open(out) as im:
        assert im.mode == "RGBA" and im.size == (300, 200)
    assert (_rgba(out) == want).all()


@pytest.mark.parametrize("size", [(1, 1), (64, 48), (3, 2000)])
def test_ac8_small_and_odd_shapes(tmp_path, size):
    """Tiny rasters (the stand-in Inkscape writes 64 x 48) and a thin one."""
    w, h = size
    im = Image.new("RGBA", size, (255, 255, 255, 0))
    im.paste((0, 0, 0, 255), (w // 4, h // 4, max(w // 4 + 1, 3 * w // 4),
                              max(h // 4 + 1, 3 * h // 4)))
    src = tmp_path / "src.png"
    im.save(src)
    cur, ref = _both(tmp_path, src)
    assert cur.shape == ref.shape
    assert _max_alpha_diff(cur, ref) <= 1


# ---------------------------------------------------------------- AC-12 ---
def test_ac12_not_much_slower(measured):
    """A guard against a pathological slowdown; the target (1.25x) is a
    reported figure in validation.md, not asserted here."""
    cur, ref = measured["current"]["seconds"], measured["reference"]["seconds"]
    assert cur <= TIME_RATIO * ref, f"{cur:.2f} s against {ref:.2f} s"


# ---------------------------------------------------------------- AC-13 ---
def test_ac13_no_new_dependencies():
    import tomllib
    deps = tomllib.loads((support.REPO / "pyproject.toml").read_text())["project"]["dependencies"]
    names = sorted(d.split(">")[0].split("=")[0].split("<")[0].strip().lower() for d in deps)
    assert names == ["numpy", "pillow", "scipy"]


# ---------------------------------------------------------- render: AC-1, 3
def _build(which, args, tmp_path, home):
    tmp_path.mkdir(parents=True, exist_ok=True)
    report, capture = tmp_path / f"{which}.json", tmp_path / f"{which}-capture"
    out = tmp_path / f"{which}-out"
    r = subprocess.run(
        [sys.executable, str(DRIVER), str(report), which, str(capture), "--",
         "-c", str(support.EXAMPLE), *args, f"--out={out}"],
        env=support.isolated_env(home), cwd=str(tmp_path),
        capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rep = json.loads(report.read_text())
    rep.update(capture=capture, out=out)
    return rep


@pytest.mark.render
def test_ac1_menkyo_process_peak_c1(inkscape, tmp_path, session_home):
    """The menkyo process's own peak (Inkscape excluded) for C-1, against the
    same build with the reference ink_layer swapped in."""
    args = C1 + ["-f", "pdf,png"]
    ref = _build("reference", args, tmp_path, session_home)
    cur = _build("current", args, tmp_path, session_home)
    print(f"\nC-1 menkyo process peak: current {cur['peak_rss'] / 1e6:.0f} MB, "
          f"reference {ref['peak_rss'] / 1e6:.0f} MB")
    assert cur["peak_rss"] <= MEMORY_RATIO * ref["peak_rss"]


@pytest.mark.render
def test_ac3_real_c1_text_layer(inkscape, tmp_path, session_home):
    """Real Inkscape text layer: the current grading against the reference's
    on the very raster Inkscape wrote."""
    rep = _build("current", C1 + ["-f", "svg"], tmp_path, session_home)
    assert len(rep["calls"]) == 1
    pre = rep["capture"] / "preink-0.png"
    cur = _rgba(rep["capture"] / "inked-0.png")
    _reference().ink_layer(str(pre), str(tmp_path / "ref.png"), 600.0)
    ref = _rgba(tmp_path / "ref.png")
    assert cur.shape == ref.shape
    assert _max_alpha_diff(cur, ref) <= 1
    _check_colour(cur, _rgba(pre))
    # what --formats svg ships next to the SVG is that same graded raster
    side = next(rep["out"].glob("*-textlayer.png"))
    assert (_rgba(side) == cur).all()
