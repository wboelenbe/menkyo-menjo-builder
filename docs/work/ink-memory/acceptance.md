# ink-memory: acceptance

The user asked: "can we optimize memory usage?". The no-inkscape spike
measured a peak of about 955 MB (cgroup `memory.peak`) for an inked A3 overlay,
about 820 MB of it in `ink.ink_layer`. This item brings that down while the
graded ink looks the same. Inkscape stays in place.

Baseline: `823af58`. A pinned copy of its `ink.py` is
`tests/acceptance/ink_memory/reference_ink.py`, and every "today" below means
that code.

## Scope

In:

- Peak memory of `src/menkyo/ink.py` (`ink_layer` and the helpers it calls).
- `_inked_text_image` in `build_diploma.py`, only where it handles the text
  raster (reading it, the `--supersample` resize, handing it to `ink_layer`).
- The `ink.py` module docstring line "composited back under the vector
  border", which `plain-white` leaves stale for this item to reword.

Out:

- The no-inkscape renderer, and the flat case's 288 MB (that belongs to the
  no-inkscape build).
- Inkscape's own memory: the text-layer export and the page PDF/PNG exports.
- Any change in how the ink looks: `MIN_DENSITY`, `FULL_AT`, the grain, the
  200 dpi field, `INK_DPI`, the seed. Not a single visible change is wanted.
- CLI flags, `--json` events, progress steps and their totals, file names, the
  SVGs. `plain-white` (built next) pins exactly one `ink` progress step per
  inked document and the totals; this item adds or splits none.
- The `-K` press colour issue and the press downsampling (DECISIONS, Open).

## Baseline figures (measured 2026-10-28, for reference)

| what | how | today |
|---|---|---|
| C-1 whole run, cgroup `memory.peak` | `menkyo-test` image, arm64 Docker on the Mac, fresh container, `-f pdf,png` | 926.5, 926.2 MB (a first, cold run: 1205 MB); spike: 916 MB |
| `ink_layer` alone, peak RSS increase | fresh process on the Mac, real C-1 text layer 7299 x 3733 | +1177 MB (tracemalloc, numpy only: 742 MB) |
| same, tiled fixture at C-1 size | `test_ac2_ink_layer_peak_memory` | +1177 MB, 1.67 s |
| `--supersample 4`, whole run | spike, Inkscape route | 4.08 GB, 15.6 s |
| `--supersample 2`, whole run | attempted | **not measured**: Docker Desktop stopped responding during this run (see Open questions, 5) |

The C-1 text layer is RGBA 7299 x 3733 (27.2 Mpx). Its RGB is not constant:
Inkscape writes 17 (`#111111`) at full coverage, 0 to 32 at the antialiased
edge, and 255 under alpha 0. The graded raster loses Inkscape's `dpi` and
`Software` PNG chunks today. Today's output is pixel-identical between macOS
arm64 and the Linux test image.

A scratch prototype of the orchestrator's approach (alpha as an L image,
`ImageChops.multiply`, RGBA rebuilt at save time, the 200 dpi field
untouched) gave +443 MB on the Mac (38 % of today) with alpha identical to
today's. So AC-2's 40 % is reachable, but only just unless the 200 dpi field
is also slimmed (its `return_indices` int64 arrays and float64 distance
transforms).

## Cases

C-1 from [docs/work/no-inkscape/acceptance.md](../no-inkscape/acceptance.md):
`-c src/menkyo/example.toml -a dan -v overlay -n ヤン・ヤンセン -r 2 -d 2024-07-01`,
with `-f pdf,png` unless a criterion says otherwise.

Fixture, `tests/acceptance/ink_memory/`:

- `textlayer-crop.png`: Inkscape's C-1 text layer before grading (example
  config, placeholder data, Docker `menkyo-test`), cropped at (5300, 0) to
  1999 x 1500: 二段, ヤン・ヤ, 段位免状; 145 KB.
- `textlayer-crop-inked-alpha.png`: today's graded alpha for it (L, 91 KB),
  pixel sha256 `8ca03fef…0758`.
- The memory tests tile the crop to 7299 x 3733, C-1's real size.

## Acceptance criteria

### Memory

- **AC-1 Whole-run peak, C-1.** One fresh container per run in the
  `menkyo-test` image (arm64 Docker on the Mac), cgroup v2 `memory.peak` at
  the end, median of 3. Target: **≤ 40 % of today's measured in the same
  image on the same day** (today ≈ 926 MB, so ≈ 370 MB). Automated proxy
  (render): the `menkyo` process's own peak RSS for C-1, Inkscape excluded,
  is ≤ 40 % of the same build with today's `ink_layer` swapped in.
- **AC-2 `ink_layer`'s own peak.** On the fixture tiled to 7299 x 3733, the
  peak-RSS increase over a fresh process's post-import baseline is ≤ 40 % of
  today's `ink_layer` measured the same way in the same test run.

### Same output

- **AC-3 Alpha.** The graded alpha differs from today's by at most 1/255 at
  every pixel: on the stored fixture reference, at C-1 size, for seeds 0, 5
  and 11, at 300 and 150 dpi (150 is below the 200 dpi field, the
  scale-1 branch), and on the real C-1 text layer Inkscape writes (render).
- **AC-4 Transparent stays transparent.** Every pixel with alpha 0 in the
  input has alpha 0 in the output. (Today's truncation turns some alpha-1
  pixels into 0; either rounding is allowed, as AC-3 allows.)
- **AC-5 Colour.** Every pixel with output alpha > 0 has R = G = B, equal
  either to the input's RGB at that pixel (today) or to the ink colour
  `#111111` (17, 17, 17) (a constant fill at save time). Composited over
  white, the result differs from today's by at most 2/255 at every pixel
  (measured: a constant fill alone costs at most 0.91/255, and AC-3 allows
  1). RGB under alpha 0 is free.
- **AC-6 Format.** The output is a PNG, mode RGBA, the same pixel size as the
  input. `ink_layer(png_path, out_path, dpi, seed=11)` keeps its signature
  and returns `out_path`, and grading in place (`png_path == out_path`, as
  `_inked_text_image` does) works.
- **AC-7 Deterministic.** Two runs on the same input, in the same process or
  in another, write byte-identical PNGs.
- **AC-8 Edge inputs.** A raster with no pixel at alpha ≥ 128 comes back with
  its pixels unchanged (as today), RGBA, same size. Tiny and thin rasters
  (1 x 1, the stand-in Inkscape's 64 x 48, 3 x 2000) work and match today's
  within AC-3.

### Supersampling

- **AC-9 `--supersample 2` and `4`.** Both still work and produce a raster of
  the 1x size, RGBA. The whole-run peak (as AC-1) at 2 and at 4 is
  **reported** in validation.md with today's figure next to it, and is not
  higher than today's. Automated (render): at 2, the graded raster has the
  1x size and its mean |Δalpha| against 1x is ≤ 0.5/255. 4 is a manual
  check (about 4 GB, too heavy for the suite).

### Nothing else changes

- **AC-10 Goldens.** `uv run pytest tests/regression` passes with no change
  to `tests/regression/` made by this item: the text-layer SVG, the chrome
  SVG, the `<image>` element, the Inkscape calls, the files written and
  stdout are byte for byte as before.
- **AC-11 CLI and `--json`.** No new or changed flag. The `--json` events,
  stage keys and progress totals are unchanged (exactly one `ink` step per
  inked document, `text` before it). Missing Inkscape still fails before
  `ink` as today. The existing suite (`test_ac_json.py`, `test_ac_cli.py`,
  `test_ac_plain_white.py` once it lands) covers this and must pass.
- **AC-12 Time (soft).** `ink_layer` on the C-1-sized input takes ≤ 1.25 x
  today's time (reported), and the suite fails above 2 x (a guard against a
  pathological slowdown). Also report the C-1 `ink` stage time and the whole
  run's wall time in Docker.
- **AC-13 No new dependency.** `[project] dependencies` are still exactly
  pillow, numpy, scipy (bounds unchanged). The installed wheel, run from
  outside the checkout, renders C-1 in Docker.
- **AC-14 Docs.** DECISIONS.md gets a dated entry: what was changed, why,
  and the before/after figures of AC-1, AC-2 and AC-9. The `ink.py` module
  docstring no longer says "composited back under the vector border" (there
  is no drawn border after `plain-white`). spike.md stays as
  it is, a record of the spike.

## Test approach

All automated tests are in `tests/acceptance/test_ac_ink_memory.py`. The
memory tests run each implementation in its own fresh subprocess and compare
ratios, so they hold on the Mac and in Docker alike. The render tests drive
`main()` through `tests/acceptance/ink_memory/ink_driver.py`, which can swap
in the pinned `ink_layer`, copies the raster before and after grading, and
reports the process's peak RSS.

| AC | automated | manual |
|---|---|---|
| AC-1 | `test_ac1_menkyo_process_peak_c1` (render) | M-1 |
| AC-2 | `test_ac2_ink_layer_peak_memory` | — |
| AC-3 | `test_ac3_alpha_matches_stored_reference`, `test_ac3_alpha_matches_reference_at_c1_size`, `test_ac3_alpha_matches_reference_other_seeds[0,5,11]`, `test_ac3_alpha_matches_reference_other_dpi[300,150]`, `test_ac3_real_c1_text_layer` (render) | — |
| AC-4 | `test_ac4_transparent_stays_transparent`, `…_at_c1_size` | — |
| AC-5 | `test_ac5_colour_is_the_ink`, `…_at_c1_size`; also inside `test_ac3_real_c1_text_layer` | — |
| AC-6 | `test_ac6_png_format`, `test_ac6_in_place` | — |
| AC-7 | `test_ac7_deterministic` | — |
| AC-8 | `test_ac8_nothing_to_grade[0,100,127]`, `test_ac8_small_and_odd_shapes[…]` | — |
| AC-9 | `test_ac9_supersample_2` (render) | M-2 |
| AC-10 | the existing `tests/regression/` suite | `git diff --stat -- tests/regression` shows nothing from this item |
| AC-11 | the existing acceptance suite | — |
| AC-12 | `test_ac12_not_much_slower` (guard at 2 x) | figures from M-1 and the `measured` print |
| AC-13 | `test_ac13_no_new_dependencies`; `test_ac_wheel.py` | M-3 |
| AC-14 | — | read DECISIONS.md and `ink.py`'s docstring |

### M-1: whole-run peak (AC-1, AC-12)

```sh
S=$(mktemp -d); git archive 823af58 src | tar -x -C "$S/"   # today, for the baseline
mkdir -p "$S/new"; cp -R src "$S/new/"                     # the working tree
docker build -f tests/docker/Dockerfile -t menkyo-test .
for src in "$S" "$S/new"; do for i in 1 2 3; do
  docker run --rm -v "$src":/menkyo:ro -e PYTHONPATH=/menkyo/src -e HOME=/tmp/h menkyo-test sh -c '
    mkdir -p /tmp/h; cd /tmp; s=$(date +%s%N)
    /opt/venv/bin/python -m menkyo -c /menkyo/src/menkyo/example.toml -a dan -v overlay \
      -n ヤン・ヤンセン -r 2 -d 2024-07-01 -f pdf,png --out /tmp/o --json > /tmp/ev
    e=$(date +%s%N); echo peak=$(cat /sys/fs/cgroup/memory.peak) wall_ms=$(( (e-s)/1000000 ))
    grep "\"stage\": \"ink\"" /tmp/ev'
done; done
```

Discard a first cold run if it is an outlier (one baseline run read 1205 MB).
Pass: median(new) ≤ 0.40 × median(today). Record both, and the ink stage
time from the progress events.

### M-2: supersampling (AC-9)

M-1's loop with `--supersample 2`, then `--supersample 4`, one run each, for
both trees. Docker Desktop must have at least 6 GB for 4. Record each peak
and wall time; pass if the new tree is not higher than today at each factor
and both runs exit 0 with the expected two files.

### M-3: wheel (AC-13)

`uv build --wheel`, install it into a throwaway venv in the test image, run
`menkyo -c <example.toml from the installed package> <C-1 args> --out /tmp/o`
from `/tmp`, with `HOME` pointed at an empty directory. Pass: exit 0, two files.
Convert page 1 of the PDF to PNG at 150 dpi and compare it with today's by
eye (the graded columns, 段位免状 and 右授与ス).

## Open questions

1. **Whole-run target if Inkscape sets the floor.** AC-1 assumes the rest of
   the C-1 run (Inkscape's 600 dpi text export, then the PDF and PNG exports
   that load the 27 Mpx raster) stays under about 370 MB. That has not been
   measured. *Recommendation:* the developer measures the floor first (M-1
   with `ink_layer` replaced by a file copy); if it is above 300 MB, AC-1
   becomes "floor + 15 %" and the user is told, with AC-2 still at 40 %.
2. **Constant ink colour versus Inkscape's RGB.** Rebuilding RGBA with
   `#111111` changes the edge pixels' RGB (0 to 32 today) by up to 0.91/255
   once composited: invisible, but the raster's bytes change. AC-5 allows
   both. *Recommendation:* allow the constant fill; it is the cheaper route
   and closer to what the colour means.
3. **Could the raster be saved as LA (grey + alpha) instead of RGBA?** It
   would halve the save-time image and the PNG, and the no-inkscape plan
   wants a DeviceGray image anyway. It changes AC-6 (mode) and what Inkscape
   embeds in the PDF. *Recommendation:* not in this item; keep RGBA, and
   raise it with the no-inkscape build.
4. **40 % or tighter.** A scratch prototype reached 38 % on `ink_layer`. The
   200 dpi field (int64 nearest-index arrays, float64 distance transforms) is
   the next large piece and is in scope. *Recommendation:* keep 40 % as the
   contract; report the figure, and tighten nothing unless the user asks.
5. **`--supersample 2` hung Docker Desktop** during this planning (the daemon
   stopped answering, not a menkyo error that was seen). Today's 2x and 4x
   figures still have to be measured, in M-2. *Recommendation:* the
   validator measures today's figures first, with Docker Desktop's memory
   limit noted; if 4x cannot run there, AC-9's "not higher than today" is
   judged on 2x and on the `menkyo` process's own peak (`ink_driver.py`).
6. **PNG metadata.** Today's graded raster drops Inkscape's `dpi` chunk.
   Nothing reads it (the `<image>` element sets the size). *Recommendation:*
   no criterion; either is fine.

## Test changes during validation (2026-10-29)

Measurement and coverage fixes; no criterion or threshold moved.

- **Peak RSS on Linux reads `VmHWM`.** `ink_driver.py` (AC-1, AC-9) and the
  `_MEASURE` helper (AC-2, AC-12) read `ru_maxrss`. On Linux that survives
  `execve`, and `subprocess` starts children through vfork, so a child
  inherits the pytest parent's peak: in the test image both builds of
  `test_ac1_menkyo_process_peak_c1` read exactly 1190039552 bytes and the
  test failed, and AC-2's post-import baseline was inflated the same way.
  Verified in `menkyo-test`: after a 1 GB allocation in the parent, a
  vfork-spawned child reads `ru_maxrss` 1011 MB and `VmHWM` 9 MB. Both now
  read `VmHWM` from `/proc/self/status` on Linux (per address space, fresh
  at exec) and keep `ru_maxrss` on macOS. The contract (40 % of the
  `menkyo` process's own peak) is unchanged.
- **AC-8 covers the early exit in place** (review R-4).
  `test_ac8_nothing_to_grade` is parametrized over a separate output and
  `png_path == out_path`, as `_inked_text_image` grades, and over RGBA, LA
  and P (with a tRNS chunk) input. It asserts RGBA, the same size, and
  unchanged pixels.
