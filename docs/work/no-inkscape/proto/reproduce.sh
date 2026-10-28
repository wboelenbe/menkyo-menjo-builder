#!/bin/bash
# Reproduce every number in docs/work/no-inkscape/spike.md (D-3 / D-4).
#
#   docs/work/no-inkscape/proto/reproduce.sh WORKDIR [STEP ...]
#
# WORKDIR must be outside the repository (e.g. /private/tmp/claude-501/...).
# With no STEP, every step runs in order (about 30 minutes on an M-series Mac
# with OrbStack; the linux/amd64 steps run under emulation). Steps:
#
#   phase1   P-1 resolution matrix (uv pip compile) for every candidate;
#            P-2 phase 1: import + ldd in python:3.13-slim-bookworm (amd64,
#            arm64), otool -L in fresh macOS venvs
#   setup    the pinned venv (requirements-dev.txt), the crest fonts
#            (fetch_fonts.sh), a read-only snapshot of HEAD 90e5799's src/
#   ref      Inkscape reference renders (Dockerfile.ref; bookworm, Inkscape
#            1.2.2, fonts-noto-cjk + fonts-noto-cjk-extra), arm64 native,
#            and the faces used: fc-match, pdffonts, embolden (G-5)
#   cand     candidate renders on macOS arm64: every case; C-9 with the
#            fallback policy; C-5 with a throwaway traced crest glyph (G-3);
#            C-5 with each crest-font option (Q-1); the runner-up (resvg)
#   compare  compare.py: G-1 G-3 G-5 V-1..V-4 + images; pdfcheck.py: F-1 F-2
#            F-3 F-5 F-6 N-1 N-2 + qpdf check; R-1 (two runs per route)
#   viewers  F-4: gs, pdftoppm (Docker), pdfium, sips and Quartz; F-6 inkcov
#   docker   P-2 phase 2 (pip-only amd64 container renders C-1 C-3 C-4 C-5,
#            dpkg empty), P-3 (same PNG with fonts-noto-cjk installed; macOS
#            vs Linux), G-4 / G-6 through the CLI with --json
#   timing   S-3 / S-4 (timing.sh, arm64 native, median of 3) and the
#            --supersample 4 run (V-3)
#   size     S-1 (apt_closure.sh, wheels.sh, fontsizes.py), S-2 (s2.sh)
#   publish  copy the comparison images into docs/work/no-inkscape/compare/
#
# Outputs: WORKDIR/run/*.json|txt|tsv hold the measured values; spike.md
# quotes them. Every render uses -c src/menkyo/example.toml (or, for G-3, a
# copy of it with traced_glyphs = true) with HOME and XDG_CONFIG_HOME
# isolated, and writes under WORKDIR only.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../../../.." && pwd)"
W="${1:?WORKDIR}"; shift; mkdir -p "$W"; W="$(cd "$W" && pwd)"
case "$W" in "$repo"*) echo "WORKDIR must be outside the repository"; exit 1;; esac
steps="${*:-phase1 setup ref cand compare viewers docker timing size publish}"
R="$W/run"; mkdir -p "$R"
py="$W/venv/bin/python"
# HOME moves so that menkyo never sees the per-user dojo.toml; Docker keeps its
# own config (contexts, buildx), or it falls back to the legacy builder, which
# mixes up the amd64 and arm64 base images.
export DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}"
export HOME="$W/home" XDG_CONFIG_HOME="$W/home/.config" MENKYO_SRC="$W/base/src" SPIKE_FONTS="$W/fonts"
mkdir -p "$HOME"
cand() { (cd "$W" && PATH=/usr/bin:/bin "$py" "$here/render_candidate.py" "$@"); }
log() { echo "== $*" >&2; }

for step in $steps; do case $step in
phase1)
  log "P-1 matrix"; mkdir -p "$W/p1"; "$here/phase1/p1.sh" "$W/p1"; cp "$W/p1/p1-matrix.txt" "$R/"
  log "P-2 phase 1, linux/amd64"; "$here/phase1/p2.sh" linux/amd64 > "$R/p2-phase1-amd64.txt" 2>&1
  log "P-2 phase 1, linux/arm64"; "$here/phase1/p2.sh" linux/arm64 > "$R/p2-phase1-arm64.txt" 2>&1
  log "P-2 phase 1, macOS"; "$here/phase1/otool.sh" "$W/otool-venvs" > "$R/p2-phase1-macos.txt" 2>&1
  ;;
setup)
  log "venv"; uv venv -q --clear -p 3.13 "$W/venv"
  uv pip install -q --python "$py" -r "$here/requirements-dev.txt"
  log "fonts"; PATH="$W/venv/bin:$PATH" "$here/fetch_fonts.sh" "$W/fonts" >/dev/null
  log "snapshot of HEAD's src/"; rm -rf "$W/base"; mkdir -p "$W/base"
  git -C "$repo" archive 90e5799 src/menkyo pyproject.toml | tar -x -C "$W/base"
  # G-3: a throwaway config with traced glyphs and one fake trace for 道
  mkdir -p "$W/traced/crest"
  sed 's/^traced_glyphs = false/traced_glyphs = true/' "$W/base/src/menkyo/example.toml" > "$W/traced/traced.toml"
  cat > "$W/traced/crest/道.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
<g transform="translate(0,100) scale(0.1,-0.1)" fill="#000000" stroke="none">
<path d="M100 100 l800 0 l0 800 l-800 0 z m150 150 l0 500 l500 0 l0 -500 z"/>
<path d="M400 400 c60 -40 140 -40 200 0 c40 60 40 140 0 200 c-60 40 -140 40 -200 0 c-40 -60 -40 -140 0 -200 z"/>
</g></svg>
SVG
  ;;
ref)
  log "reference renders"; "$here/render_reference.sh" "$R/ref" > "$R/ref.log" 2>&1
  docker run --rm -v "$W/base":/menkyo:ro -v "$here":/proto:ro -v "$W/traced":/traced:ro -v "$R/ref-traced":/out \
    -e SPIKE_CONFIG=/traced/traced.toml menkyo-spike-ref:arm64 python /proto/ref_driver.py /out C-5 >> "$R/ref.log" 2>&1
  docker run --rm -v "$R/ref":/out -v "$W/base/src/menkyo/fonts":/yf:ro menkyo-spike-ref:arm64 bash -c '
    inkscape --version 2>/dev/null; dpkg-query -W fonts-noto-cjk fonts-noto-cjk-extra fontconfig libcairo2 inkscape
    printf "%s\n" "<?xml version=\"1.0\"?><!DOCTYPE fontconfig SYSTEM \"urn:fontconfig:fonts.dtd\"><fontconfig><include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include><dir>/yf</dir><cachedir>/tmp/fc</cachedir></fontconfig>" > /tmp/fc.conf
    export FONTCONFIG_FILE=/tmp/fc.conf
    echo "== fc-match crest"; fc-match "Noto Serif CJK JP SemiBold:weight=180"; fc-match -v "Noto Serif CJK JP SemiBold:weight=180" | grep -E "file:|embolden"
    for w in 80 100 180; do echo "== Yuji Boku fc weight $w"; fc-match -v "Yuji Boku:weight=$w" | grep -E "fullname:|weight:|embolden"; done
    for c in C-1 C-4 C-5 C-9; do echo "== pdffonts $c"; pdffonts /out/$c/*.pdf; done
    for c in C-1 C-3 C-4; do echo "ref inkcov $c: $(gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=inkcov -o - /out/$c/*.pdf | tr -s " ")"; done' > "$R/ref-faces.txt" 2>&1
  ;;
cand)
  log "candidate renders"; cand "$R/cand" C-1 C-3 C-4 C-4b C-5 C-8 C-9 > "$R/cand.log" 2>&1
  SPIKE_MISSING=fallback cand "$R/cand-fallback" C-9 >> "$R/cand.log" 2>&1
  SPIKE_CONFIG="$W/traced/traced.toml" cand "$R/cand-traced" C-5 >> "$R/cand.log" 2>&1
  SPIKE_FONT_CREST="$W/fonts/NotoSerifCJKjp-SemiBold.otf" cand "$R/cand-crest-cjk" C-5 >> "$R/cand.log" 2>&1
  SPIKE_FONT_CREST="$W/fonts/NotoSerifJP-wght600.ttf" cand "$R/cand-crest-gf600" C-5 >> "$R/cand.log" 2>&1
  SPIKE_RASTER=resvg cand "$R/resvg" C-1 C-3 C-4 C-5 C-8 >> "$R/cand.log" 2>&1
  grep -E '^C-' "$R/cand.log"
  ;;
compare)
  log "compare.py"; L="fontTools + own PDF writer + pdfium"
  "$py" "$here/compare.py" "$R/ref" "$R/cand" "$W/img" "$R/metrics.json" --label "$L" > "$R/compare.log"
  "$py" "$here/compare.py" "$R/ref" "$R/cand-fallback" "$W/img-fallback" "$R/metrics-fallback.json" --label "$L, fallback" --cases C-9 >> "$R/compare.log"
  "$py" "$here/compare.py" "$R/ref-traced" "$R/cand-traced" "$W/img-traced" "$R/metrics-traced.json" --label "$L, traced 道" --cases C-5 >> "$R/compare.log"
  for t in cand-crest-cjk cand-crest-gf600; do
    "$py" "$here/compare.py" "$R/ref" "$R/$t" "$W/img-$t" "$R/metrics-$t.json" --label "$t" --cases C-5 >> "$R/compare.log"; done
  "$py" "$here/compare.py" "$R/ref" "$R/resvg" "$W/img-resvg" "$R/metrics-resvg.json" --label "runner-up: resvg" >> "$R/compare.log"
  log "pdfcheck.py"; "$py" "$here/pdfcheck.py" props "$R/ref" "$R/cand" > "$R/props.jsonl"
  log "R-1"; cand "$R/cand2" C-1 C-4 > /dev/null 2>&1
  docker run --rm -v "$W/base":/menkyo:ro -v "$here":/proto:ro -v "$R/ref2":/out menkyo-spike-ref:arm64 python /proto/ref_driver.py /out C-1 C-4 > /dev/null 2>&1
  : > "$R/r1.txt"
  for t in cand ref; do for c in C-1 C-4; do
    a=$(ls "$R/$t/$c"/*.pdf); b=$(ls "$R/${t}2/$c"/*.pdf)
    echo "$t $c pdf $("$py" "$here/pdfcheck.py" same "$a" "$b")" >> "$R/r1.txt"
    echo "$t $c png $("$py" "$here/pdfcheck.py" samepng "${a%.pdf}.png" "${b%.pdf}.png")" >> "$R/r1.txt"
  done; done; cat "$R/r1.txt"
  ;;
viewers)
  log "F-4 viewers"; "$here/viewers.sh" "$R/cand" "$R/viewers" > "$R/viewers.txt" 2>&1
  "$py" "$here/compare.py" viewers "$R/cand" "$R/viewers" "$R/viewers.json" >> "$R/viewers.txt"
  ;;
docker)
  log "P-2 phase 2 / P-3"
  (cd "$here" && docker build -q --platform linux/amd64 -f Dockerfile.cand -t menkyo-spike-cand:amd64 . \
     && docker build -q --platform linux/arm64 -f Dockerfile.cand -t menkyo-spike-cand:arm64 . \
     && docker build -q --platform linux/amd64 --build-arg BASE=menkyo-spike-cand:amd64 -f Dockerfile.cand-fonts -t menkyo-spike-cand-fonts:amd64 .) > /dev/null
  mounts=(-v "$W/base":/menkyo:ro -v "$here":/proto:ro -v "$W/fonts":/fonts:ro)
  docker run --rm --platform linux/amd64 "${mounts[@]}" -v "$R/p2amd64":/out menkyo-spike-cand:amd64 sh -c '
    uname -m; echo "dpkg matches: $(dpkg -l | grep -Eic "cairo|pango|rsvg|poppler|fontconfig|ghostscript|inkscape")"
    ls /usr/share/fonts 2>&1 | head -1; python /proto/render_candidate.py /out C-1 C-3 C-4 C-5 2>&1 | grep -E "^C-"' > "$R/p2amd64.txt" 2>&1
  docker run --rm --platform linux/arm64 "${mounts[@]}" -v "$R/p2arm64":/out menkyo-spike-cand:arm64 sh -c '
    uname -m; echo "dpkg matches: $(dpkg -l | grep -Eic "cairo|pango|rsvg|poppler|fontconfig|ghostscript|inkscape")"
    python /proto/render_candidate.py /out C-1 C-3 C-4 C-5 2>&1 | grep -E "^C-"' > "$R/p2arm64.txt" 2>&1
  docker run --rm --platform linux/amd64 "${mounts[@]}" -v "$R/p3fonts":/out menkyo-spike-cand-fonts:amd64 sh -c '
    echo "fonts: $(fc-list | wc -l) faces; fc-match crest: $(fc-match "Noto Serif CJK JP SemiBold")"
    python /proto/render_candidate.py /out C-1 2>&1 | grep -E "^C-"' > "$R/p3fonts.txt" 2>&1
  c=dan-overlay-2-ヤン-ヤンセン
  { for e in png pdf; do
      echo "C-1 $e amd64 no fonts vs amd64 fonts-noto-cjk: $("$py" "$here/pixdiff.py" "$R/p2amd64/C-1/$c.$e" "$R/p3fonts/C-1/$c.$e")"
      echo "C-1 $e macOS arm64 vs linux amd64: $("$py" "$here/pixdiff.py" "$R/cand/C-1/$c.$e" "$R/p2amd64/C-1/$c.$e")"
      echo "C-1 $e linux arm64 vs linux amd64: $("$py" "$here/pixdiff.py" "$R/p2arm64/C-1/$c.$e" "$R/p2amd64/C-1/$c.$e")"
    done; } > "$R/p3.txt"; cat "$R/p2amd64.txt" "$R/p3fonts.txt" "$R/p3.txt"
  log "G-4 / G-6 through the CLI"
  g="$R/g46"; rm -rf "$g"; mkdir -p "$g"
  head -c 3000000 "$W/base/src/menkyo/fonts/YujiBoku-Regular.ttf" > "$g/truncated-YujiBoku.ttf"
  head -c 2000000 "$W/fonts/NotoSerifJP-SemiBold.otf" > "$g/truncated-crest.otf"
  ex="$W/base/src/menkyo/example.toml"
  c9=(-a dan -v overlay-flat -n "𠮷田・ファン・デル・フェルデン" -r 10 -d 2020-10-20 -f pdf,png)
  blank=(-a dan -v overlay -f pdf -n '' -r '' -d '')
  demo() { local t="$1"; shift; echo "## $t"; set +e; env "$@" 2>&1; echo "exit=$?"; set -e; }
  { demo "G-4 missing glyph, error policy, --json" PATH=/usr/bin:/bin "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o1" --json "${c9[@]}"
    demo "G-4 missing glyph, fallback policy, --json" SPIKE_MISSING=fallback PATH=/usr/bin:/bin "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o6" --json "${c9[@]}"
    demo "G-6 body font missing, --json" SPIKE_FONT_BODY=/nonexistent/YujiBoku-Regular.ttf "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o2" --json "${blank[@]}"
    demo "G-6 body font truncated, --json" SPIKE_FONT_BODY="$g/truncated-YujiBoku.ttf" "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o3" --json "${blank[@]}"
    demo "G-6 crest font truncated, --json" SPIKE_FONT_CREST="$g/truncated-crest.otf" "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o4" --json "${blank[@]}"
    demo "G-6 crest font missing, plain" SPIKE_FONTS=/nonexistent "$py" "$here/render_candidate.py" --cli -- -c "$ex" --out "$g/o5" "${blank[@]}"
    for d in o1 o2 o3 o4 o5; do echo "left in $d: $(ls -A "$g/$d" 2>/dev/null | tr '\n' ' ')"; done
  } > "$R/g46.txt"; cat "$R/g46.txt"
  ;;
timing)
  log "S-3 / S-4"; "$here/timing.sh" "$R/timing.tsv" 3 "C-1 C-4"
  "$here/timing.sh" "$R/timing-ss4.tsv" 1 "C-1-ss4"
  ;;
size)
  log "S-1 apt closure"; "$here/apt_closure.sh" > "$R/apt.txt" 2>&1; cat "$R/apt.txt"
  log "S-1 / P-1 wheels"; "$here/wheels.sh" "$W/wheels" > "$R/wheels.txt" 2>&1; cut -c1-60 "$R/wheels.txt"
  ls -l "$W"/wheels/*/ | awk '/pypdfium2|fonttools/ {print $5, $NF}' | sort -u > "$R/wheel-sizes.txt"
  "$py" "$here/fontsizes.py" "$W/fonts" > "$R/fontsizes.txt"; cat "$R/fontsizes.txt"
  log "S-2 images"; "$here/s2.sh" "$W/s2" > "$R/s2.txt" 2>&1; cat "$R/s2.txt"
  ;;
publish)
  out="$here/../compare"; mkdir -p "$out"
  cp "$W"/img/*.png "$out/"
  cp "$W/img-fallback/C-9_overlay-flat_side-by-side.png" "$out/C-9-fallback_overlay-flat_side-by-side.png"
  cp "$W/img-fallback/C-9_crops.png" "$out/C-9-fallback_crops.png"
  cp "$W/img-traced/C-5_crops.png" "$out/C-5-traced-glyph_crops.png"
  du -ch "$out"/*.png | tail -1
  ;;
*) echo "unknown step $step"; exit 2;;
esac; done
