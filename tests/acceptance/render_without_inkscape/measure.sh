#!/bin/sh
# Whole-run peak memory and wall time, one fresh container per run
# (render-without-inkscape, acceptance.md AC-24 and AC-25).
#
#   measure.sh IMAGE SRC PYTHON [RUNS] [PLATFORM]
#
#   IMAGE     a Docker image with menkyo's dependencies installed
#   SRC       a directory holding src/menkyo (the working tree, or a
#             `git archive` snapshot); mounted read-only
#   PYTHON    the interpreter in the image: /opt/venv/bin/python in
#             menkyo-test, python in the reference image
#   RUNS      runs per case (default 3)
#   PLATFORM  docker --platform (default: the native one)
#
# Prints one line per run: case, cgroup v2 memory.peak in MB, wall milliseconds, exit code,
# then the median per case.  Every run pins -c example.toml and passes
# --name, --rank and --date; HOME is a throwaway inside the container.
set -eu
image="$1"; src="$(cd "$2" && pwd)"; py="$3"; runs="${4:-3}"; plat="${5:-}"
C1="-a dan -v overlay -n ヤン・ヤンセン -r 2 -d 2024-07-01"
C4="-a dan -v overlay-flat -n アレクサンドル・ファン・デル・フェルデン -r 10 -d 2020-10-20"
C5="-a dan -v proof --name= --rank= --date="
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
for spec in "C-1|$C1 -f pdf,png" "C-1p|$C1 -f pdf" "C-4|$C4 -f pdf,png" \
            "C-4p|$C4 -f pdf" "C-5|$C5 -f pdf,png"; do
  case_id="${spec%%|*}"; args="${spec#*|}"
  i=0
  while [ "$i" -lt "$runs" ]; do
    i=$((i + 1))
    docker run --rm ${plat:+--platform "$plat"} -v "$src":/menkyo:ro \
      -e PYTHONPATH=/menkyo/src -e HOME=/tmp/h -e XDG_CONFIG_HOME=/tmp/h/.config \
      "$image" sh -c "
        mkdir -p /tmp/h/.config; cd /tmp
        s=\$(date +%s%N)
        $py -m menkyo -c /menkyo/src/menkyo/example.toml $args --out /tmp/o --json > /tmp/ev
        rc=\$?; e=\$(date +%s%N)
        tail -n 1 /tmp/ev | grep -q '\"event\": \"done\"' || rc=99
        echo \"$case_id \$(( \$(cat /sys/fs/cgroup/memory.peak) / 1048576 )) \$(( (e - s) / 1000000 )) \$rc\"
      " | tee -a "$tmp"
  done
done
echo "--- median per case: peak MB, wall ms"
for c in C-1 C-1p C-4 C-4p C-5; do
  peak=$(awk -v c="$c" '$1 == c {print $2}' "$tmp" | sort -n | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}')
  wall=$(awk -v c="$c" '$1 == c {print $3}' "$tmp" | sort -n | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}')
  echo "$c $peak $wall"
done
