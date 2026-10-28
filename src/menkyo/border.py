#!/usr/bin/env python3
"""
Engraved phoenix-plume border, drawn from scratch.

A fallback for when blank Japanese certificate stock (賞状用紙) cannot be
sourced: it lets the whole diploma be printed on plain cream paper.

The motif language is taken from the 2002 diploma's own border (see
ref/diploma_antonio_rectified.jpg) rather than copied from it — long phoenix
plumes with herringbone barbs along a spine, peacock eye-feathers at intervals,
and small florets filling the gaps, all in fine engraved line work.

Everything is generated, so the band width, density and motif mix are all
parameters.  Nothing here is traced from the commercial stock.
"""

import math

# ---------------------------------------------------------------- geometry --


def _rounded_rect_path(x0, y0, x1, y1, r):
    """Clockwise samples of a rounded rectangle: [(point, unit tangent), ...].

    In SVG's y-down space the inward normal of a clockwise walk is
    (-ty, tx), which every motif below relies on.
    """
    segs = []
    segs.append(("line", (x0 + r, y0), (x1 - r, y0)))
    segs.append(("arc", (x1 - r, y0 + r), -90.0, 0.0))
    segs.append(("line", (x1, y0 + r), (x1, y1 - r)))
    segs.append(("arc", (x1 - r, y1 - r), 0.0, 90.0))
    segs.append(("line", (x1 - r, y1), (x0 + r, y1)))
    segs.append(("arc", (x0 + r, y1 - r), 90.0, 180.0))
    segs.append(("line", (x0, y1 - r), (x0, y0 + r)))
    segs.append(("arc", (x0 + r, y0 + r), 180.0, 270.0))
    return segs, r


def _walk(segs, r, step):
    """Yield (point, tangent) every `step` mm along the closed path."""
    out, carry = [], 0.0
    for seg in segs:
        if seg[0] == "line":
            (ax, ay), (bx, by) = seg[1], seg[2]
            L = math.hypot(bx - ax, by - ay)
            if L < 1e-9:
                continue
            tx, ty = (bx - ax) / L, (by - ay) / L
            s = carry
            while s < L:
                out.append(((ax + tx * s, ay + ty * s), (tx, ty)))
                s += step
            carry = s - L
        else:
            (cx, cy), a0, a1 = seg[1], seg[2], seg[3]
            L = math.radians(a1 - a0) * r
            s = carry
            while s < L:
                a = math.radians(a0) + s / r
                p = (cx + r * math.cos(a), cy + r * math.sin(a))
                t = (-math.sin(a), math.cos(a))
                out.append((p, t))
                s += step
            carry = s - L
    return out


def _bez(p0, p1, p2, p3, t):
    u = 1 - t
    x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
    dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1])
    m = math.hypot(dx, dy) or 1.0
    return (x, y), (dx / m, dy / m)


# ------------------------------------------------------------------ motifs --


def plume(bx, by, dx, dy, length, width, curve=0.35, barb=1.05,
          barb_angle=62.0, eye=False, lw=0.13):
    """One phoenix plume: a curved spine carrying herringbone barbs.

    (dx, dy) is the direction of the spine at its base; `curve` bends the tip
    sideways so a run of plumes reads as overlapping feathers on a wing.
    """
    nx, ny = -dy, dx                      # left of the spine direction
    p0 = (bx, by)
    p3 = (bx + dx * length + nx * curve * length,
          by + dy * length + ny * curve * length)
    p1 = (bx + dx * length * 0.40, by + dy * length * 0.40)
    p2 = (bx + dx * length * 0.80 + nx * curve * length * 0.55,
          by + dy * length * 0.80 + ny * curve * length * 0.55)

    spine = (f"M {p0[0]:.2f} {p0[1]:.2f} C {p1[0]:.2f} {p1[1]:.2f} "
             f"{p2[0]:.2f} {p2[1]:.2f} {p3[0]:.2f} {p3[1]:.2f}")
    d = []

    n = max(6, int(length / barb))
    ca, sa = math.cos(math.radians(barb_angle)), math.sin(math.radians(barb_angle))
    for i in range(1, n):
        t = i / n
        (px, py), (tx, ty) = _bez(p0, p1, p2, p3, t)
        # barbs sweep outward and forward, giving the herringbone
        prof = math.sin(math.pi * t ** 0.75) * (1.0 - 0.3 * t)
        L = width * prof
        if L < 0.25:
            continue
        for sgn in (1, -1):
            ux = tx * ca + (-ty) * sa * sgn
            uy = ty * ca + (tx) * sa * sgn
            d.append(f"M {px:.2f} {py:.2f} L {px+ux*L:.2f} {py+uy*L:.2f}")

    out = [f'<path d="{" ".join(d)}" fill="none" stroke-width="{lw*0.85:.3f}"/>',
           f'<path d="{spine}" fill="none" stroke-width="{lw*1.7:.3f}"/>']
    if eye:
        (ex, ey), (tx, ty) = _bez(p0, p1, p2, p3, 0.88)
        ang = math.degrees(math.atan2(ty, tx))
        rx, ry = width * 0.62, width * 0.46
        g = [f'<g transform="translate({ex:.2f} {ey:.2f}) rotate({ang:.1f})">']
        for k, f in enumerate((1.0, 0.66, 0.38)):
            g.append(f'<ellipse rx="{rx*f:.2f}" ry="{ry*f:.2f}" fill="none" '
                     f'stroke-width="{lw*(1.0 if k else 1.3):.3f}"/>')
        g.append(f'<ellipse rx="{rx*0.20:.2f}" ry="{ry*0.20:.2f}" stroke="none"/>')
        g.append("</g>")
        out.append("".join(g))
    return "".join(out)


def floret(cx, cy, r, petals=5, rot=0.0, lw=0.13):
    """A small hatched star-flower, as along the foot of the original."""
    d = []
    for i in range(petals):
        a = math.radians(rot + i * 360.0 / petals)
        a1, a2 = a - math.pi / petals, a + math.pi / petals
        tipx, tipy = cx + math.cos(a) * r, cy + math.sin(a) * r
        b1 = (cx + math.cos(a1) * r * 0.40, cy + math.sin(a1) * r * 0.40)
        b2 = (cx + math.cos(a2) * r * 0.40, cy + math.sin(a2) * r * 0.40)
        d.append(f"M {b1[0]:.2f} {b1[1]:.2f} Q {tipx:.2f} {tipy:.2f} {b2[0]:.2f} {b2[1]:.2f}")
    return (f'<path d="{" ".join(d)}" fill="none" stroke-width="{lw}"/>'
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r*0.17:.2f}" stroke="none"/>')


def berry_sprig(bx, by, dx, dy, length, lw=0.13):
    """A stem with round berries, the filler motif on the original's foot."""
    nx, ny = -dy, dx
    tip = (bx + dx * length, by + dy * length)
    ctl = (bx + dx * length * 0.5 + nx * length * 0.28,
           by + dy * length * 0.5 + ny * length * 0.28)
    out = [f'<path d="M {bx:.2f} {by:.2f} Q {ctl[0]:.2f} {ctl[1]:.2f} '
           f'{tip[0]:.2f} {tip[1]:.2f}" fill="none" stroke-width="{lw}"/>']
    for t in (0.45, 0.72, 1.0):
        u = 1 - t
        px = u * u * bx + 2 * u * t * ctl[0] + t * t * tip[0]
        py = u * u * by + 2 * u * t * ctl[1] + t * t * tip[1]
        out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{0.16*length:.2f}" '
                   f'fill="none" stroke-width="{lw}"/>')
    return "".join(out)


def seam_lozenge(cx, cy, h, lw=0.13):
    """A small pierced lozenge closing the mirror seam, echoing the club mon."""
    def dia(r):
        return (f"M {cx:.2f} {cy-r:.2f} L {cx+r:.2f} {cy:.2f} "
                f"L {cx:.2f} {cy+r:.2f} L {cx-r:.2f} {cy:.2f} Z")
    return (f'<path d="{dia(h)} {dia(h*0.62)}" fill-rule="evenodd" '
            f'stroke="none"/>'
            f'<path d="{dia(h*1.34)}" fill="none" stroke-width="{lw*1.6:.3f}"/>')


# ------------------------------------------------------------------ border --


def border_svg(page_w, page_h, rule_inset=8.0, band_in=12.0, band_out=34.0,
               corner=15.0, colour="#8a6a33", density=13.0, seed=7, uid="bd"):
    """The whole engraved frame.

    Every motif is clipped to the band itself, so the weave reads as one
    deliberate ribbon rather than a spray of loose feathers.
    """
    rnd = _Rng(seed)
    bw = band_out - band_in
    ci, co = corner, max(0.0, corner - (band_out - band_in))
    o = []

    # the band is an annulus: outer rounded rect minus inner rounded rect
    o.append(f'<defs><clipPath id="{uid}" clip-rule="evenodd"><path d="'
             f'{_rrect_d(band_in, band_in, page_w-band_in, page_h-band_in, ci)} '
             f'{_rrect_d(band_out, band_out, page_w-band_out, page_h-band_out, co)}"'
             f'/></clipPath>'
             f'<clipPath id="{uid}h"><rect x="0" y="0" width="{page_w/2:.2f}" '
             f'height="{page_h}"/></clipPath></defs>')

    half = []
    o_real, o = o, half

    segs, r = _rounded_rect_path(band_in, band_in, page_w - band_in,
                                 page_h - band_in, corner)

    # outer row: long plumes leaning across the band, overlapping like a wing
    for i, (p, t) in enumerate(_walk(segs, r, density)):
        if p[0] > page_w / 2 + 70.0:
            continue
        nx, ny = -t[1], t[0]                       # inward
        th = math.radians(34.0 + rnd.jitter(2.5))
        dx = t[0] * math.cos(th) + nx * math.sin(th)
        dy = t[1] * math.cos(th) + ny * math.sin(th)
        o.append(plume(p[0], p[1], dx, dy, bw * (2.10 + rnd.jitter(0.12)),
                       bw * 0.42, curve=-0.22, barb=0.72,
                       eye=(i % 4 == 1)))

    # inner row: shorter, out of phase, thickening the inner half of the band
    for i, (p, t) in enumerate(_walk(segs, r, density)):
        if p[0] > page_w / 2 + 50.0:
            continue
        nx, ny = -t[1], t[0]
        bx = p[0] + nx * bw * 0.30 + t[0] * density * 0.5
        by = p[1] + ny * bw * 0.30 + t[1] * density * 0.5
        th = math.radians(30.0 + rnd.jitter(2.5))
        dx = t[0] * math.cos(th) + nx * math.sin(th)
        dy = t[1] * math.cos(th) + ny * math.sin(th)
        o.append(plume(bx, by, dx, dy, bw * (1.25 + rnd.jitter(0.10)),
                       bw * 0.24, curve=-0.20, barb=0.78))

    # florets and berry sprigs riding the inner edge, as on the original's foot
    for i, (p, t) in enumerate(_walk(segs, r, density * 0.5)):
        if p[0] > page_w / 2 + 12.0:
            continue
        nx, ny = -t[1], t[0]
        fx, fy = p[0] + nx * bw * 0.88, p[1] + ny * bw * 0.88
        if i % 2 == 0:
            o.append(floret(fx, fy, bw * 0.13, rot=rnd.jitter(180.0)))
        else:
            o.append(berry_sprig(fx, fy, t[0], t[1], bw * 0.30))

    # The 2002 border is symmetric about the vertical axis, with the wings
    # sweeping in from both sides: draw the left half, mirror it for the right.
    body = "\n".join(half)
    o = o_real
    o.append(f'<g stroke="{colour}" fill="{colour}" stroke-linecap="round" '
             f'clip-path="url(#{uid})">')
    o.append(f'<g clip-path="url(#{uid}h)">{body}</g>')
    o.append(f'<g transform="translate({page_w} 0) scale(-1 1)" '
             f'clip-path="url(#{uid}h)">{body}</g>')
    mid = (band_in + band_out) / 2.0
    for cy in (mid, page_h - mid):
        o.append(seam_lozenge(page_w / 2.0, cy, bw * 0.19))
    o.append("</g>")

    # rules: a double rule outside the band, a hairline closing it inside
    o.append(f'<g stroke="{colour}" fill="none" stroke-linecap="square">')
    for ins, lw in ((rule_inset, 0.5), (rule_inset + 1.7, 0.22),
                    (band_out + 1.4, 0.28)):
        rad = max(0.0, corner + band_in - ins)
        o.append(f'<rect x="{ins}" y="{ins}" width="{page_w-2*ins}" '
                 f'height="{page_h-2*ins}" rx="{rad:.1f}" stroke-width="{lw}"/>')
    o.append("</g>")
    return "\n".join(o)


def _rrect_d(x0, y0, x1, y1, r):
    """Rounded rectangle as path data, for use inside a clipPath."""
    return (f"M {x0+r:.2f} {y0:.2f} H {x1-r:.2f} A {r:.2f} {r:.2f} 0 0 1 {x1:.2f} {y0+r:.2f} "
            f"V {y1-r:.2f} A {r:.2f} {r:.2f} 0 0 1 {x1-r:.2f} {y1:.2f} "
            f"H {x0+r:.2f} A {r:.2f} {r:.2f} 0 0 1 {x0:.2f} {y1-r:.2f} "
            f"V {y0+r:.2f} A {r:.2f} {r:.2f} 0 0 1 {x0+r:.2f} {y0:.2f} Z")


class _Rng:
    """Tiny deterministic jitter source, so every rebuild is byte-identical."""

    def __init__(self, seed):
        self.s = seed

    def jitter(self, amp):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s / 0x7FFFFFFF - 0.5) * 2.0 * amp


if __name__ == "__main__":
    W, H = 420.0, 297.0
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
           f'viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#faf5e9"/>'
           + border_svg(W, H) + "</svg>")
    open("../build/border-test.svg", "w").write(svg)
    print("wrote ../build/border-test.svg")
