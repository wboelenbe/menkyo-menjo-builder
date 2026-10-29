#!/bin/sh
# Render the Inkscape reference fixtures for render-without-inkscape.
#
#   tests/acceptance/render_without_inkscape/make_reference.sh [COMMIT]
#
# COMMIT defaults to 8509b85, the last commit rendered by Inkscape.  Its
# src/ is extracted with `git archive` into a temporary directory and mounted
# read-only, so neither the working tree nor a dojo.toml reaches the
# container.  Writes reference/ beside this script.  Needs Docker; the image
# is Dockerfile.ref (Inkscape 1.2.2 with the crest's Noto Serif CJK JP
# SemiBold), native platform.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
commit="${1:-8509b85}"
snap="$(mktemp -d)"
trap 'rm -rf "$snap"' EXIT
git -C "$repo" archive "$commit" src/menkyo | tar -x -C "$snap"
docker build -q -f "$here/Dockerfile.ref" -t menkyo-inkscape-ref "$here" >/dev/null
rm -rf "$here/reference"
mkdir -p "$here/reference"
docker run --rm -e REF_COMMIT="$commit" -e MENKYO_SRC=/menkyo/src \
  -v "$snap":/menkyo:ro -v "$here":/kit:ro -v "$here/reference":/out \
  menkyo-inkscape-ref python /kit/ref_render.py /out
du -sh "$here/reference"
