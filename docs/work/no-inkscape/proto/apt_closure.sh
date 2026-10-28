#!/bin/bash
# S-1: installed size (dpkg Installed-Size, KiB) of the closure that
#   apt-get install --no-install-recommends inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra
# pulls into python:3.13-slim-bookworm (linux/amd64), then with ghostscript too.
set -eu
docker run --rm --platform linux/amd64 python:3.13-slim-bookworm sh -c '
  sum() { dpkg-query -W -f="\${Package} \${Installed-Size}\n" | sort > /tmp/$1; }
  sum base; apt-get update -qq
  apt-get install -y -qq --no-install-recommends inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra >/dev/null 2>&1; sum ink
  apt-get install -y -qq --no-install-recommends ghostscript >/dev/null 2>&1; sum gs
  for t in ink gs; do comm -13 /tmp/base /tmp/$t | awk -v t=$t "{s+=\$2; n++} END {printf \"%s: %d packages, %.1f MB installed (dpkg Installed-Size)\n\", t, n, s/1024}"; done
  comm -13 /tmp/base /tmp/ink | sort -k2 -n -r | head -8 | awk "{printf \"   %s %.1f MB\n\", \$1, \$2/1024}"
  dpkg-query -W fonts-noto-cjk fonts-noto-cjk-extra inkscape'
