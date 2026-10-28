#!/bin/bash
# Build the reference image and render every case with Inkscape.
#   render_reference.sh OUTDIR [platform]       (default platform linux/arm64)
# OUTDIR must not be inside the repository. The menkyo source is a read-only
# snapshot of HEAD (git archive), so the parallel work in src/ cannot move it.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../../../.." && pwd)"
out="$1"; plat="${2:-linux/arm64}"
snap="$(mktemp -d)"; git -C "$repo" archive 90e5799 src/menkyo pyproject.toml | tar -x -C "$snap"
docker build -q --platform "$plat" -f "$here/Dockerfile.ref" -t menkyo-spike-ref:${plat#linux/} "$here" >/dev/null
mkdir -p "$out"
docker run --rm --platform "$plat" -v "$snap":/menkyo:ro -v "$here":/proto:ro -v "$out":/out \
  menkyo-spike-ref:${plat#linux/} python /proto/ref_driver.py /out C-1 C-3 C-4 C-4b C-5 C-8 C-9
rm -rf "$snap"
