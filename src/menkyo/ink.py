#!/usr/bin/env python3
"""
Sumi-ink simulation for the printed columns.

A brush font gives the *shape* of calligraphy but prints as flat black. Real
sumi is denser where the brush pressed and thinner *and greyer* where it lifted
— the two go together, because a lifting brush lays down both a narrower stroke
and less ink. That relationship is recoverable from the glyph geometry alone:

    local stroke thickness  ->  ink density

The measure has to be *local thickness* — the diameter of the largest disc that
fits inside the stroke and covers this point (Hildebrand & Rüegsegger) — not
distance-to-edge, which would emboss every stroke by darkening its spine, and
not a medial axis propagated outward, which leaves visible seams where the
nearest-ridge regions meet. Those seams read as scratches straight through the
strokes; it is the first thing that goes wrong here.

Thickness is then normalised per connected stroke, so the award formula at
40 mm and the authority block at 12 mm come out looking like the same brush.

Used by build_diploma.py: the text layer is rendered on its own, inked here,
and composited back under the vector border.
"""

import numpy as np
from PIL import Image
from scipy import ndimage

# How pale a fully lifted brush tip is allowed to get.  Tuned by sweeping
# against the 2002 diploma: real sumi is very black, with the variation living
# in a narrow band near the tips.  Push this much lower and the thin strokes
# stop reading as ink and start reading as a failing printer.
MIN_DENSITY = 0.76

# Fraction of a stroke's own typical thickness at which ink is already solid.
FULL_AT = 0.64

# Dry-brush grain: amplitude, and the blur radius that sets its scale, in mm.
NOISE_AMP = 0.05
NOISE_MM = 0.30

# The density field is smooth and low-frequency, so it is computed at this
# resolution and interpolated back up. Keeps the local-thickness sweep cheap.
WORK_DPI = 200.0


def local_thickness(mask, steps=26):
    """Diameter of the largest inscribed disc covering each point, in pixels.

    For every candidate radius r, the points whose distance-to-edge is at least
    r are the centres of inscribed discs of that size; everything within r of
    such a centre is covered by one. Sweeping r downwards and keeping the first
    (largest) hit gives each pixel the thickness of the stroke it sits in —
    smoothly, with no seams, because it is a union of discs rather than a
    nearest-neighbour partition.
    """
    dist = ndimage.distance_transform_edt(mask)
    dmax = float(dist.max())
    if dmax <= 0:
        return dist
    out = np.zeros(mask.shape, dtype=np.float32)
    for r in np.linspace(dmax, 0.6, steps):
        centres = dist >= r
        if not centres.any():
            continue
        covered = ndimage.distance_transform_edt(~centres) <= r
        fill = covered & mask & (out == 0)
        if fill.any():
            out[fill] = 2.0 * r
    out[mask & (out == 0)] = 2.0 * dist[mask & (out == 0)]
    return out


def _per_stroke_reference(mask, thickness):
    """Each stroke's own typical thickness, so glyph size cancels out.

    A brush stroke is usually its own connected component, and each one tapers
    on its own terms — so normalising per component is both physically right
    and what makes a 12 mm kanji and a 40 mm one read as the same hand.
    """
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    ref = np.zeros(mask.shape, dtype=np.float32)
    if n == 0:
        return ref + 1.0
    for sl, i in zip(ndimage.find_objects(lab), range(1, n + 1)):
        if sl is None:
            continue
        sub = lab[sl] == i
        vals = thickness[sl][sub]
        if vals.size:
            # 90th percentile, not the max: a single blob of ink at a stroke's
            # shoulder should not decide the whole stroke is thin.
            ref[sl][sub] = float(np.percentile(vals, 90)) or 1.0
    ref[ref <= 0] = 1.0
    return ref


def ink_layer(png_path, out_path, dpi, seed=11):
    """Turn a flat-black text render into graded sumi.

    `png_path` is an RGBA render of the text alone on transparency; its alpha
    carries glyph coverage, so the renderer's antialiasing survives intact.
    """
    im = Image.open(png_path).convert("RGBA")
    a = np.array(im)
    cov = a[..., 3].astype(np.float32) / 255.0
    if not (cov > 0.5).any():
        im.save(out_path)
        return out_path

    # --- density field, computed small ------------------------------------
    scale = min(1.0, WORK_DPI / float(dpi))
    small = (max(1, int(a.shape[1] * scale)), max(1, int(a.shape[0] * scale)))
    m = np.array(Image.fromarray((cov * 255).astype(np.uint8)).resize(
        small, Image.BILINEAR)) > 128

    thick = local_thickness(m)
    ref = _per_stroke_reference(m, thick)
    rel = np.clip(thick / (ref * FULL_AT), 0.0, 1.0)
    rel = rel * rel * (3.0 - 2.0 * rel)                     # smoothstep

    # Extend the field outward before it is blurred or scaled up. Outside the
    # stroke `rel` is 0, i.e. maximally lifted; leave that in place and the
    # blur and the bicubic upsample both drag it inward, ringing every glyph
    # with a pale halo that reads as a soft, ragged edge. Giving each outside
    # pixel its nearest inside value means the edge inherits the density of
    # the ink it borders, and the outline stays as crisp as the renderer drew
    # it.
    outside = ndimage.distance_transform_edt(
        ~m, return_distances=False, return_indices=True)
    rel = rel[tuple(outside)]

    density = MIN_DENSITY + (1.0 - MIN_DENSITY) * rel

    rng = np.random.default_rng(seed)
    grain = ndimage.gaussian_filter(
        rng.standard_normal(m.shape).astype(np.float32),
        max(1.0, NOISE_MM * WORK_DPI / 25.4))
    grain /= np.abs(grain).max() or 1.0
    density += grain * NOISE_AMP * (1.0 - rel)              # grain where it lifts
    density = ndimage.gaussian_filter(np.clip(density, 0.4, 1.0), 1.2)

    # --- back up to full resolution ---------------------------------------
    dens = np.array(Image.fromarray(
        (np.clip(density, 0, 1) * 255).astype(np.uint8)
    ).resize((a.shape[1], a.shape[0]), Image.BICUBIC)).astype(np.float32) / 255.0

    out = a.copy()
    out[..., 3] = np.clip(cov * dens * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(out_path)
    return out_path
