# ink-memory: review

## Round 1

Verdict: APPROVE. No blocker or major findings. The code is correct, and the
claim that the graded alpha is bit for bit unchanged holds.

**What was checked:**
- **Full suite:** `uv run pytest` gives 337 passed and 12 skipped. All 12
  skips are render tests (no Inkscape on the Mac).
- **Memory and time:** reference +1176 MB in 1.71 s, current +263 MB in
  1.66 s, matching the DECISIONS table.
- **Bit-exact alpha:** the new `ink_layer` against the pinned
  `reference_ink.py` at 600 and 150 dpi gives max diff 0 for:
  - the fixture crop;
  - crops 257 and 255 rows high (not a multiple of `_BAND`, and fewer rows
    than one band);
  - LA, L and P inputs;
  - a fully opaque RGBA image, an empty transparent image, a 1 x 1 image.
- **Equivalences:**
  - The early exit `getextrema()[1] < 128` equals the old
    `(cov > 0.5).any()`.
  - The old `float32(v)/255*255` round trip is exact for 0..255, so feeding
    `cov` straight to the 200 dpi resize gives the same mask.
  - `_edt` does SciPy's arithmetic (int32 index difference, float64,
    dy² + dx², sqrt); the developer tests check exact equality.
  - The banded multiply keeps the float32 operation order.
- **`--supersample`:** resizing the alpha alone equals the old RGBA resize,
  since Pillow resamples the alpha channel on its own.
- **Rules and contract:** fixtures are example-config placeholder data and
  the driver pins `-c` with an isolated env; no CLI flag, `--json` event or
  progress step changed; `tests/regression/` untouched; no commits.

**[R-1] minor, contract/docs.** DECISIONS.md, the "whole run, C-1, cgroup
`memory.peak` (Docker)" row says "not yet measured". AC-14 asks for before
and after figures for AC-1, and AC-9 for whole-run Docker peaks at
`--supersample` 2 and 4. The render tests
`test_ac1_menkyo_process_peak_c1`, `test_ac3_real_c1_text_layer` and
`test_ac9_supersample_2` have not run against this change (Docker was hung).
Fix: run `scripts/test-docker.sh` plus M-1 and M-2 and fill in the table
before the commit.

**[R-2] nit, structure.** `src/menkyo/build_diploma.py:551-556` and
`src/menkyo/ink.py:138-142` repeat the same block (open, `load()`, convert
to RGBA if needed, `getchannel("A")`). Optional: a small helper in `ink.py`
used by both.

**[R-3] nit, docs.** DECISIONS.md:512-513, "Pillow resizes RGBA
premultiplied, band by band": "band" means a Pillow channel here, while the
same entry uses "a band of rows" for the row strips. Write "channel by
channel".

## Round 2

Verdict: APPROVE. `coverage()` and the new early exit are correct; the
DECISIONS figures are self-consistent and state the fallback honestly.

**What was checked:**
- `uv run pytest -W error::ResourceWarning`: 337 passed, 12 skipped
  (render tests, no Inkscape on the Mac).
- `ink.coverage()`: `im.load()` closes Pillow's handle; L, LA,
  P-with-transparency and I;16 inputs convert correctly; the RGBA image is
  released on return, so `--supersample` never holds both renders.
- Early exit graded in place: byte-identical to the pinned reference for
  RGBA, LA and P-with-transparency inputs; output RGBA, same size.
- DECISIONS arithmetic: 437/927 = 47 %, 221/944 = 23 %, 263/1176 = 22 %;
  437 MB is 0.5 % above the 435 MB floor; floor + 15 % = 500 MB applies
  (open question 1).

**[R-4] minor, tests.** The early exit with `png_path == out_path` has no
test (`test_ac6_in_place` grades; `test_ac8_nothing_to_grade` writes to a
separate file with RGBA input only). Passed to the tester, who owns the
file.

**[R-5] nit, docs.** The "`menkyo` process alone" row is peak RSS of
`ink_driver.py` while the row above is cgroup `memory.peak`, so the part
(944 MB) reads larger than the whole (927 MB). Fixed by the orchestrator:
the row now names the measure.

**[R-6] nit, docs.** `tests/test_ink_memory.py` still said "band by band".
Fixed by the orchestrator: "channel by channel".
