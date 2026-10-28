#!/bin/bash
# P-1: full transitive closure, binary only, 3 Pythons x 3 platforms, per candidate.
# Each candidate's set includes menkyo's own runtime deps (pillow numpy scipy).
# usage: p1.sh OUTDIR   (writes OUTDIR/in, OUTDIR/out, OUTDIR/p1-matrix.txt)
cd "${1:?OUTDIR}"
rm -rf in out; mkdir -p in out
while read -r k pkgs; do printf '%s\n' pillow numpy scipy $pkgs > in/$k.in; done <<'L'
lead_fonttools_pdfium fonttools pypdfium2
resvg_py fonttools resvg-py
skia_python skia-python
pikepdf pikepdf
reportlab reportlab
svglib svglib
fpdf2 fpdf2
cairosvg cairosvg
pymupdf pymupdf
ghostscript ghostscript
matplotlib matplotlib
L
for f in in/*.in; do k=$(basename $f .in); for py in 3.11 3.12 3.13; do for plat in aarch64-apple-darwin x86_64-manylinux_2_28 aarch64-manylinux_2_28; do
  if uv pip compile -q --only-binary :all: --python-version $py --python-platform $plat --no-header --no-annotate $f -o out/$k-$py-$plat.txt >out/$k-$py-$plat.log 2>&1; then r=OK; else r=FAIL; fi
  echo "$k $py $plat $r"; done; done; done | sort > p1-matrix.txt
