#!/bin/bash
# P-1 file names and S-1 download sizes: pip download, binary only, full
# closure of requirements.txt, per Python and platform (explicit tags).
# pip is run under the matching Python, since --python-version does not
# change how environment markers (numpy/scipy per Python) are evaluated.
# macOS needs macosx_13_0_arm64 as well: pypdfium2 5.14 has no 11_0 wheel.
#   wheels.sh OUTDIR
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; out="$1"; mkdir -p "$out"
for py in 3.11 3.12 3.13; do
  for plat in "mac:--platform macosx_13_0_arm64 --platform macosx_11_0_arm64" \
              "linux-x86_64:--platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64" \
              "linux-aarch64:--platform manylinux_2_28_aarch64 --platform manylinux_2_17_aarch64 --platform manylinux2014_aarch64"; do
    name=${plat%%:*}; tags=${plat#*:}; d="$out/$py-$name"
    if uvx --quiet --python $py pip==25.2 download --quiet --only-binary=:all: --python-version $py $tags \
         -r "$here/requirements.txt" -d "$d" >"$d.log" 2>&1; then r=OK; else r=FAIL; fi
    echo "$py $name $r: $(ls "$d" 2>/dev/null | tr '\n' ' ')"
  done
done
