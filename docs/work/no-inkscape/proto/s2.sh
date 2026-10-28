#!/bin/bash
# S-1 (menkyo wheel before/after) and S-2 (slim runtime images, linux/amd64).
#   s2.sh WORKDIR       needs SPIKE_FONTS (fetch_fonts.sh) for the crest font
# "before": HEAD's wheel + apt inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra
# "after":  HEAD's wheel with the crest font vendored and fonttools + pypdfium2
#           added to its dependencies -- pip only. Neither is the real build;
#           both are what it would install.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../../../.." && pwd)"; w="$1"
rm -rf "$w"; mkdir -p "$w/before" "$w/after" "$w/ctx-before" "$w/ctx-after"
git -C "$repo" archive 90e5799 src/menkyo pyproject.toml README.md LICENSE NOTICE | tar -x -C "$w/before"
git -C "$repo" archive 90e5799 src/menkyo pyproject.toml README.md LICENSE NOTICE | tar -x -C "$w/after"
cp "$SPIKE_FONTS/NotoSerifJP-SemiBold.otf" "$w/after/src/menkyo/fonts/"
cp "$SPIKE_FONTS/LICENSE-noto-cjk.txt" "$w/after/src/menkyo/fonts/OFL-NotoSerifJP.txt"
python3 - "$w/after/pyproject.toml" <<'PY'
import sys; p = sys.argv[1]; s = open(p).read()
s = s.replace('    "scipy>=1.8",\n]', '    "scipy>=1.8",\n    "fonttools>=4.50",\n    "pypdfium2>=4.30",\n]', 1)
open(p, "w").write(s)
PY
(cd "$w/before" && uv build -q --wheel --out-dir "$w/ctx-before")
(cd "$w/after" && uv build -q --wheel --out-dir "$w/ctx-after")
ls -l "$w"/ctx-*/*.whl | awk '{print "wheel", $NF, $5}'
cat > "$w/ctx-before/Dockerfile" <<'D'
FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
      inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra && rm -rf /var/lib/apt/lists/*
COPY *.whl /tmp/
RUN pip install --no-cache-dir --root-user-action=ignore /tmp/*.whl && rm /tmp/*.whl
D
cat > "$w/ctx-after/Dockerfile" <<'D'
FROM python:3.13-slim-bookworm
COPY *.whl /tmp/
RUN pip install --no-cache-dir --root-user-action=ignore /tmp/*.whl && rm /tmp/*.whl
D
docker build -q --platform linux/amd64 -t menkyo-spike-s2:before "$w/ctx-before" >/dev/null
docker build -q --platform linux/amd64 -t menkyo-spike-s2:after "$w/ctx-after" >/dev/null
for t in before after; do echo "image $t $(docker image inspect -f '{{.Size}}' menkyo-spike-s2:$t)"; done
echo "image base $(docker image inspect -f '{{.Size}}' python:3.13-slim-bookworm)"
docker run --rm --platform linux/amd64 menkyo-spike-s2:after sh -c 'cd /usr/local/lib/python3.13/site-packages && du -sk pypdfium2 pypdfium2_raw fontTools menkyo numpy numpy.libs scipy scipy.libs PIL pillow.libs | sort -n'
# docker image inspect's .Size is unreliable with the containerd image store
# (it reported 153 MB and 602 MB for the same "after" image), so the numbers
# that count are the unpacked filesystem and the uncompressed layer tarball:
for t in python:3.13-slim-bookworm menkyo-spike-s2:before menkyo-spike-s2:after; do
  du=$(docker run --rm --platform linux/amd64 "$t" sh -c 'du -sxk / 2>/dev/null | cut -f1')
  tar=$(docker save --platform linux/amd64 "$t" | wc -c)
  echo "$t: unpacked $((du/1024)) MB (du -sxk /), docker save $((tar/1048576)) MB"
done
