"""Developer tests for ink-memory: the pieces the lower peak rests on.

The acceptance tests compare ink_layer's output and memory with the pinned
823af58 copy; these pin the assumptions that make the output identical:
ink._edt gives SciPy's distances exactly, and the graded raster is the ink
colour under the graded alpha.
"""

import numpy as np
import pytest
from PIL import Image
from scipy import ndimage

from menkyo import build_diploma as bd
from menkyo import ink


def _masks():
    rng = np.random.default_rng(3)
    blobs = ndimage.gaussian_filter(rng.random((700, 900)), 4) > 0.5
    yield "blobs", blobs                     # more than one band of rows
    yield "speckle", rng.random((300, 5)) > 0.3
    yield "one", np.ones((1, 1), bool)
    yield "full", np.ones((40, 30), bool)    # no background at all
    yield "empty", np.zeros((40, 30), bool)
    yield "row", rng.random((1, 600)) > 0.5


@pytest.mark.parametrize("name", [n for n, _ in _masks()])
def test_edt_is_scipys_distance_exactly(name):
    mask = dict(_masks())[name]
    want = ndimage.distance_transform_edt(mask)
    got = ink._edt(mask)
    assert got.dtype == want.dtype and got.shape == want.shape
    assert np.array_equal(got, want)


@pytest.mark.parametrize("r", [0.6, 1.0, 2.5, 7.3, 31.0])
def test_edt_within_is_the_same_comparison(r):
    mask = dict(_masks())["blobs"]
    want = ndimage.distance_transform_edt(~mask) <= r
    got = ink._edt(~mask, within=r)
    assert got.dtype == bool
    assert np.array_equal(got, want)


def test_ink_colour_is_the_generators():
    assert "#%02x%02x%02x" % ink.INK == bd.INK.lower()


def test_graded_raster_is_the_ink_under_the_alpha(tmp_path):
    src = tmp_path / "src.png"
    im = Image.new("RGBA", (200, 120), (255, 255, 255, 0))
    im.paste((0, 0, 0, 255), (40, 20, 160, 100))
    im.save(src)
    out = tmp_path / "out.png"
    assert ink.ink_layer(str(src), str(out), 600.0) == str(out)
    got = np.array(Image.open(out))
    assert got.shape == (120, 200, 4)
    assert (got[..., :3] == ink.INK).all()
    assert got[..., 3].max() > 0 and (got[..., 3][:20] == 0).all()
