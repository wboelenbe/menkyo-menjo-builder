#!/bin/bash
# F-4 (and F-6's inkcov): rasterise the candidate PDFs at 150 dpi in other
# viewers. Ghostscript and poppler run in the reference image (Docker);
# Quartz runs natively, both through sips and through CoreGraphics directly.
#   viewers.sh CANDTREE OUTDIR
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; cand="$(cd "$1" && pwd)"; out="$2"; mkdir -p "$out"; out="$(cd "$out" && pwd)"
for c in C-1 C-3 C-4 C-5; do
  pdf=$(ls "$cand/$c"/*.pdf); cp "$pdf" "$out/$c.pdf"
  sips -s format png -z 1754 2480 "$out/$c.pdf" --out "$out/$c-sips.png" >/dev/null
  swift "$here/quartz_render.swift" "$out/$c.pdf" "$out/$c-quartz.png" 150
done
docker run --rm -v "$out":/v menkyo-spike-ref:arm64 sh -c '
  cd /v; for c in C-1 C-3 C-4 C-5; do
    gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r150 -dTextAlphaBits=4 -dGraphicsAlphaBits=4 -o $c-gs.png $c.pdf
    pdftoppm -r 150 -png -singlefile $c.pdf $c-poppler
    echo "inkcov $c: $(gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=inkcov -o - $c.pdf | tr -s " ")"
  done; gs --version | sed "s/^/gs /"; pdftoppm -v 2>&1 | head -1'
