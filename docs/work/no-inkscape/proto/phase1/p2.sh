#!/bin/bash
# P-2 phase 1: per candidate, a fresh python:3.13-slim-bookworm, pip install only, import + ldd.
# usage: p2.sh linux/amd64|linux/arm64
plat=$1; here="$(cd "$(dirname "$0")" && pwd)"
while read -r k pkgs mod; do
  docker run --rm --platform $plat -v "$here":/p2:ro python:3.13-slim-bookworm sh -c \
    "pip install -q --root-user-action=ignore --only-binary=:all: $pkgs >/tmp/pip.log 2>&1 || { echo '[$mod] pip install FAILED'; tail -3 /tmp/pip.log; exit 0; }; python /p2/ldd_check.py $mod; dpkg -l | grep -Eic 'cairo|pango|rsvg|poppler|fontconfig|ghostscript|inkscape' | sed 's/^/   dpkg matches: /'"
done <<'L'
lead pypdfium2==5.14.0 pypdfium2
lead fonttools==4.68.0 fontTools.ttLib
resvg resvg-py==0.5.0 resvg_py
skia skia-python==144.1 skia
pikepdf pikepdf pikepdf
reportlab reportlab==5.1.0 reportlab.graphics.renderPDF
svglib svglib==2.3.2 svglib.svglib
fpdf2 fpdf2 fpdf
cairosvg cairosvg==2.9.1 cairosvg
pymupdf pymupdf pymupdf
ghostscript ghostscript==0.8.1 ghostscript
pillow pillow==13.0.0 PIL.ImageFont
matplotlib matplotlib matplotlib.backends.backend_pdf
L
