#!/bin/bash
# S-3 / S-4: wall clock and peak memory per certificate, both routes, native
# linux/arm64 Docker (no emulation), one fresh container per run, median of 3.
#   timing.sh OUT.tsv [RUNS] [CASES]     default: 3 runs of C-1 C-4
# Columns: route case run process_ms inprocess_s memory_peak_bytes stages
# process_ms is `python driver.py` from start to exit (imports included);
# the stages are the --json stage keys with their start times (s).
set -eu
here="$(cd "$(dirname "$0")" && pwd)"; repo="$(cd "$here/../../../.." && pwd)"
out="$1"; runs="${2:-3}"; cases="${3:-C-1 C-4}"
snap="$(mktemp -d)"; git -C "$repo" archive 90e5799 src/menkyo pyproject.toml | tar -x -C "$snap"
fonts="${SPIKE_FONTS:?set SPIKE_FONTS to the fetch_fonts.sh directory}"
run() {  # route image driver case
  docker run --rm --platform linux/arm64 -v "$snap":/menkyo:ro -v "$here":/proto:ro -v "$fonts":/fonts:ro \
    -e MENKYO_SRC=/menkyo/src -e SPIKE_FONTS=/fonts "$2" sh -c "
    s=\$(date +%s%N); python /proto/$3 /tmp/out $4 >/dev/null 2>&1; e=\$(date +%s%N)
    python -c 'import json,sys; d=json.load(open(\"/tmp/out/$4/stages.json\")); print(round(d[\"wall\"],3), json.dumps([(k, round(t,2)) for k,t in d[\"stages\"]]))' > /tmp/st
    echo \"\$(( (e-s)/1000000 )) \$(cut -d' ' -f1 /tmp/st) \$(cat /sys/fs/cgroup/memory.peak) \$(cut -d' ' -f2- /tmp/st)\""
}
: > "$out"
for i in $(seq $runs); do for c in $cases; do
  echo -e "ref\t$c\t$i\t$(run ref menkyo-spike-ref:arm64 ref_driver.py $c | tr ' ' '\t' | sed 's/\t\[/ [/')" >> "$out"
  echo -e "cand\t$c\t$i\t$(run cand menkyo-spike-cand:arm64 render_candidate.py $c | tr ' ' '\t' | sed 's/\t\[/ [/')" >> "$out"
done; done
rm -rf "$snap"; cat "$out"
