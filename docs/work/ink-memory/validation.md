# ink-memory: validation

## Round 1 (2026-10-29)

**Verdict: PASS.** AC-1 passes on the contract's fallback, not on its
40 % target: the whole run is at 47 % of today's peak, because Inkscape sets
a floor of 441 MB that the ink pass cannot go below (see AC-1).

Environment: macOS arm64 (no Inkscape), and the `menkyo-test` image on
OrbStack (Docker 29.8.2, 16.8 GB, 18 CPUs; Inkscape 1.2.2, Python 3.13). Every
render pins `-c src/menkyo/example.toml` (or the installed copy of it) with
`HOME` and `XDG_CONFIG_HOME` pointed at an empty directory. MB means 10^6
bytes.

### Test fixes made before this round (recorded in acceptance.md)

- **Driver peak on Linux.** I confirmed the developer's diagnosis in
  `menkyo-test`. After the parent allocates 1 GB:
  - a child spawned through `subprocess` (vfork) reads `ru_maxrss`
    1011474432 bytes and `VmHWM` 9449472;
  - with a forced fork (`preexec_fn`) the child reads `ru_maxrss` 9461760.

  `ink_driver.py` and the AC-2 `_MEASURE` helper now read `VmHWM` on Linux.
  The `_MEASURE` helper had the same flaw: its baseline was inherited from
  pytest.
- **R-4.** `test_ac8_nothing_to_grade` now covers grading in place, and LA
  and P input.

### Suites

- `uv run pytest` (Mac): **352 passed, 12 skipped**. All 12 skips are render
  tests (Inkscape is not installed).
- `scripts/test-docker.sh`: **362 passed, 2 skipped**. The 2 skips are
  `test_ac_cli_only.py:50` and `:296`, which need git history; the image has
  no `.git`. No render test was skipped (`REQUIRE_RENDER=1`).
- `git status -- tests/regression`: clean.

### Per criterion

| AC | result | evidence |
|---|---|---|
| AC-1 | **PASS (fallback: floor + 15 %)** | Today's tree measured 933 MB, the new tree 442 MB, which is **47 %** against the 40 % target. The floor is 441 MB, and the target is out of reach because of it; details in the M-1 section below. The fallback allows 1.15 × 441 = 507 MB, and 442 MB is within it. Automated proxy in Docker: the `menkyo` process alone peaks at 221 MB against 948 MB, which is 23 % (≤ 40 %). |
| AC-2 | PASS | Mac: +263 MB against +1176 MB (22 %). Docker: +160 MB against +886 MB (18 %). |
| AC-3 | PASS | The suite passes on the Mac and in Docker; the real C-1 layer is covered by `test_ac3_real_c1_text_layer` in Docker. M-3: the text layer from the installed wheel against the one from 823af58 has a max alpha diff of **0**. Beyond the suite, 102 cases match the reference bit for bit (max diff 0): 8 heights (1, 2, 255, 256, 257, 511, 513, 700) × 3 widths × 4 dpi values (600, 300, 150, 72), random strokes, plus fully opaque input, all-alpha-128 input, and seeds 0, 1, 2^31-1 and 2^40. |
| AC-4 | PASS | Suite tests, plus the 102 cases above: no output alpha above 0 where the input was 0. |
| AC-5 | PASS | In the real C-1 layer, every inked pixel is (17, 17, 17). Over white, the largest difference from today's layer is 0.914/255 (≤ 2). |
| AC-6 | PASS | Suite tests. The real layer is a PNG, RGBA, 7299 × 3733. |
| AC-7 | PASS | `test_ac7_deterministic` passes, both in the same process and in another. |
| AC-8 | PASS | The extended test passes (54 parametrizations): alpha 0, 100 and 127; RGBA, LA and P input; output to a separate file and in place. Also passes for small and odd shapes. |
| AC-9 | PASS | `test_ac9_supersample_2` (Docker): mean \|Δalpha\| 0.0545/255 (≤ 0.5), size 1x, RGBA. Whole-run peaks are in the M-2 table below; both factors exit 0 and write 2 files. |
| AC-10 | PASS | The regression suite passes on the Mac and in Docker; `tests/regression/` is unchanged. |
| AC-11 | PASS | The diff touches no flag or event. Suite passes, including `test_ac_json.py` and `test_ac_cli.py`. Every M-1 run gave exactly the stages `text`, `ink`, `pdf`, `png` and ended with `done`. |
| AC-12 | PASS | Time is unchanged or slightly better; figures below. |
| AC-13 | PASS | Dependencies are unchanged against 823af58 (numpy>=1.22, pillow>=9.0, scipy>=1.8); `test_ac13` passes. M-3: the wheel, installed into a fresh venv in the image and run from `/tmp` with an empty `HOME`, exits 0. It writes the PDF and the PNG and ends with a `done` event. The wheel's `ink.py` is the working tree's. |
| AC-14 | PASS | DECISIONS.md has the entry "2026-10-29 — The ink pass grades the alpha alone", with before and after figures for AC-1, AC-2 and AC-9. `ink.py` no longer says "composited back under the vector border". `spike.md` is unchanged since 823af58. |

AC-12 figures:

| | today | new | ratio |
|---|---|---|---|
| `ink_layer`, C-1 size, Mac | 1.66 s | 1.62 s | 0.98× |
| `ink_layer`, C-1 size, Docker | 2.05 s | 1.91 s | 0.93× |
| C-1 `ink` stage, Docker (median of 3) | 1.67 s | 1.61 s | |
| C-1 whole run, wall time, Docker (median of 3) | 3.82 s | 3.77 s | |

### M-1: whole-run peak (AC-1, AC-12)

Each run used a fresh container and read cgroup `memory.peak` at the end.
The stage times come from the `--json` progress events, timestamped as they
arrive.

| tree | peaks, MB | median | wall time (median) | `ink` stage |
|---|---|---|---|---|
| today (823af58) | 957, 932, 933 | **933** | 3.82 s | 1.67 s |
| new (working tree) | 445, 441, 442 | **442** | 3.77 s | 1.61 s |
| floor: new tree, `ink_layer` replaced by a file copy | 442, 441, 440 | **441** | 2.12 s | 0.00 s |

The evidence supports the fallback, so the statement that "the run now
peaks in Inkscape" holds:

- **The floor.** With the grading reduced to a file copy, the run still
  peaks at 441 MB. That is above 300 MB, so open question 1 applies.
- **The ink pass adds nothing measurable.** The new tree peaks within
  1 MB of the floor.
- **The rest comes from Inkscape.** The `menkyo` process alone peaks at
  221 MB (driver, `VmHWM`), so the remainder of the cgroup peak is
  Inkscape.

My figures are about 5 MB above the developer's 437 / 435 MB; the
difference is the same for both and does not change the conclusion. The
user should be told that the 40 % target became floor + 15 %.

### M-2: supersampling (AC-9)

One run per tree and factor; all four exited 0 and wrote 2 files.

| | today | new |
|---|---|---|
| `--supersample 2`, peak | 1433 MB | **603 MB** |
| `--supersample 2`, wall time | 7.02 s | 6.46 s |
| `--supersample 4`, peak | 4096 MB | **2242 MB** |
| `--supersample 4`, wall time | 15.31 s | 14.00 s |

The new tree is not higher than today at either factor.

### M-3: wheel and how the output looks

- **Setup.** `uv build --wheel` gave `menkyo-0.2.0-py3-none-any.whl`. I
  installed it into a fresh venv in `menkyo-test` and ran C-1 from `/tmp`
  with `-c` set to the installed `example.toml`.
- **Result.** Exit 0; the `done` event lists the PDF and the PNG.
- **Visual check.** I compared page 1 of the PDF (pdftoppm, 150 dpi) and the
  page PNG with the same build from 823af58, by eye and by numbers:
  - The graded columns (段位免状, 二段, 右授与ス, ヤン・ヤンセン殿) look the
    same.
  - The page PNG composited over white differs by at most 1.83/255, and its
    alpha is identical.

### New finding, not in contract (minor, no action proposed)

When poppler renders the PDF, a few antialiased edge pixels come out
slightly darker than today's: up to 7/255 at 150 dpi (75 pixels), 9/255 at
300 dpi (912 pixels out of 17.4 M), and 7/255 at 600 dpi (126 pixels in a
2500 × 3000 crop).

- **Likely cause.** The PDF holds the image as RGB plus a soft mask. Today's
  raster has white under alpha 0; the new one has `#111111`. A renderer that
  interpolates the colour and the mask separately therefore picks up a
  little of that colour at the stroke's edge. AC-5 leaves the RGB under
  alpha 0 free, and the graded raster itself is within AC-5.
- **Is it visible?** No. At 4x zoom the before and after edges cannot be
  told apart; the differing pixels are isolated, single and sparse. The new
  behaviour is arguably the more faithful one, since the old white fringe
  lightened the edges in the same way.
- **What would remove it.** Writing white under alpha 0 would restore
  today's bytes. Recorded for the user; not a failure.
