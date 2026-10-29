VERDICT: PASS

# paper-format: validation

## Round 1

Validated against `acceptance.md`: the user decisions, AC-1 to AC-21, the
Agreement and the User approval (OQ-1 to OQ-7 as recommended). The working
tree is on `bc92fbe` plus the uncommitted change. Every render used
`-c src/menkyo/example.toml` or a configuration the test wrote, with HOME
and XDG_CONFIG_HOME in the scratchpad. Nothing was written to the
repository's `build/`.

### Suites

- `uv run pytest` (Mac): **730 passed**, 235 s.
- `scripts/test-docker.sh` (menkyo-test, linux/arm64): **724 passed, 6
  skipped**. All six skips are the git-history tests
  (`test_ac_cli_only.py:53` and `:305`, `test_ac_house_style_sweep.py:42`
  and `:273`, `test_ac_render_without_inkscape.py:260` and `:1073`). No
  render test skipped.
- In `tests/acceptance` and `tests/regression`, the diff holds only the
  tester's own edits. The thresholds in `test_ac_paper_format.py` are as
  agreed: AC-9 at 0.3 mm and 15/20, AC-12 at 0.60–1.40 and 8, AC-13 at
  0.9.

### Per AC

| AC | result | evidence |
|---|---|---|
| 1 | PASS | `test_ac1_help_lists_paper`. The help reads "--paper SIZE  the sheet, landscape: a3 or a4, … (default: a3, from [paper] size in the configuration)". The epilog says "on plain white A3 or A4". |
| 2 | PASS | `test_ac2_*`: `--paper=a3` writes the same bytes as no flag (PDF, PNG, SVG, all three variants). |
| 3 | PASS | `test_ac3_*`, including `test_ac3_upper_case_accepted`. By hand, `size = "A4"` gives `dan-overlay-a4-sample.pdf` and `--paper a3` overrides it. `save()` writes `size = "a4"` under `[paper]`. |
| 4 | PASS | `test_ac4_*`. By hand: `--paper b5 --clean` exits 2 and keeps `keep.pdf`; under `--json` it is one `error` ("argument --paper: invalid choice: 'b5' (choose from 'a3', 'a4')") with exit 1. `--json --paper` with no value gives "expected one argument". |
| 5 | PASS | `test_ac5_*`. By hand: "…/bad.toml: [paper] size = "a5" is not a paper size; use "a3" or "a4"", exit 1, also with `--list --paper a3`. `size = 4` under `--json` gives one `error` and writes nothing. |
| 6 | PASS | `test_ac6_*`, all nine name cases, `planned`, `file`, `done` and `wrote`. |
| 7 | PASS | `test_golden.py` passes through `sized()`, all 14 render cases and 16 list cases. `sized()` is idempotent (`test_ac7_sized_name_mapping`). |
| 8 | PASS | `test_ac8_*`. By hand with pypdfium2: the A4 overlay and proof are 841.89 × 595.276 pt (297.0 × 210.0 mm); A3 is 1190.551 × 841.89 pt. The A4 SVG root is `width="297.0mm" height="210.0mm" viewBox="0 0 297.0 210.0"`, then `<g transform="scale(0.7071067812)">`. |
| 9 | PASS | Docker printout, with bbox differences in mm and the mean absolute difference over drawn pixels: filled 0.10, 3.85; blank 0.10, 3.80; proof 0.07, 4.85; licence with a long name 0.05, 4.11; inked 0.10, 9.23; traced crest 0.10, 3.74; custom margins 0.17, 4.97. Limits: 0.3 mm, 15 (20 inked). |
| 10 | PASS | `test_ac10_*` (3508 × 2480, 1754 × 1240, 4961 × 3508, the same pHYs). By hand, A4 at 150 dpi is 1754 × 1240 with dpi 150.01. |
| 11 | PASS | `test_ac11_text_layer_600_dpi`. By hand, the A3 text layer is 7299 × 3734 and the A4 one 5161 × 2641 (× 0.7071 = 5161.2 × 2640.4). |
| 12 | PASS | Docker printout: lifted share A3 0.0296, A4 0.0227 (ratio 0.767, limit 0.60–1.40); 5th percentile 233 against 237 (limit 8); mean 251.41 against 251.72 (limit 1.5). The Mac gives the same values. |
| 13 | PASS | Docker `peak_driver`: A3 199 MB, A4 154 MB (77 %, limit 90 %). See M-4. |
| 14 | PASS | `test_ac14_json_events_same_but_names`. By hand, the wheel's A4 `--json` stream has the same progress steps and labels as A3. |
| 15 | PASS | `test_ac15_all_variants_a4`. By hand, `--paper=a4 -v all --list` lists the overlay, overlay-flat and proof names with `-a4-sample`. |
| 16 | PASS | `test_ac16_deterministic`. |
| 17 | PASS | `test_ac17_glyph_check_first`. |
| 18 | PASS | Regression goldens (see AC-7), `test_ac_render_without_inkscape.py` and `test_ac2_explicit_a3_is_the_default_bytes`. |
| 19 | PASS | `test_ac19_installed_wheel_a4` (slow) and M-5. |
| 20 | PASS | `test_ac20_help_flags`, `test_ac23_help_offers_todays_options`, and `test_ac7_cli_help_unchanged` on the Mac. |
| 21 | PASS | `test_ac21_*`, plus the house-style lint and `test_ac11_history_pinned`. The new DECISIONS entry "2026-10-29 – A4 as well as A3" names what it overrides, the naming and its reason, OQ-4's numbers and the measurements. The Open item is gone. The `example.toml` `[paper]` comment says the values are A3 millimetres and scale on A4. |

### Manual checks

- **M-1, look at it.** `-a dan -v overlay,proof -f png --paper a4 --dpi 150
  -d 2026-09-05`, against A3 at 106 dpi (1753 × 1239 against 1754 × 1240),
  composited on white side by side. The overlay and the proof are the same
  sheet: crest, heading, 五段, ジョン・ドウ殿, 右授与ス, the date and the
  authority block all in the same place. On the proof, the border and
  safe-inset guides and the seal circle are scaled with everything else.
- **M-2, page size.** Measured with pypdfium2 (see AC-8): 297.0 × 210.0 mm.
- **M-3, ink at print size.** The A4 text layer at 600 dpi beside the A3
  one, downscaled with Lanczos to the same pixels, cropped to 右授 and 五段.
  The brush lifts sit in the same places and the edges are as crisp. The
  A4 is no darker or blotchier to the eye.
- **M-4, memory and time.** `measure.sh`, plus `--paper` passed through an
  `EXTRA` variable in a scratchpad copy. menkyo-test, median of 3:

  | case | A3 | A4 |
  |---|---|---|
  | C-1, overlay, PDF + PNG | 218 MB, 3.38 s | 141 MB, 2.08 s |
  | C-1p, the portal's run | 187 MB, 3.18 s | 141 MB, 2.13 s |
  | C-4, overlay-flat, PDF + PNG | 63 MB, 0.44 s | 63 MB, 0.44 s |
  | C-4p, overlay-flat, PDF | 58 MB, 0.32 s | 58 MB, 0.34 s |
  | C-5, proof, PDF + PNG | 63 MB, 0.49 s | 66 MB, 0.49 s |

  C-4p and C-5 came out a hair higher at A4, so I ran each five more times
  at both sizes. C-4p: A3 57–58 MB and 233–254 ms, A4 57–58 MB and
  234–253 ms. C-5: A3 63 MB and 398–436 ms, A4 63–64 MB and 332–351 ms. Both
  differences are noise, and A4 is never above A3 beyond it. The
  inked runs drop by about a quarter in memory and a third in time. These
  agree with the figures in the DECISIONS entry (C-1p 188 against 142 MB).
- **M-5, installed wheel.** `uv build --wheel` gave
  `menkyo-0.4.0-py3-none-any.whl`, installed into a throwaway venv and run
  from `/tmp` with an isolated HOME:
  - `--version` prints 0.4.0.
  - `--paper a4 --list` lists three `-a4-sample` PDFs.
  - `--paper=A4 -a dan -v overlay` writes
    `~/Documents/Menkyo/dan-overlay-a4-sample.pdf`, 297 × 210 mm.
  - The portal's form (`--config=… --awards=dan --variants=overlay
    --formats=pdf --name=ヤン・ヤンセン --rank=二段 --date=2026-09-05
    --out=… --json --paper=a4`) gives progress text/ink/pdf, then
    `file` and `done` for `dan-overlay-a4-二段-ヤン-ヤンセン.pdf`, 297 × 210 mm.

### Edge cases tried

- `--paper A4` / `--paper=a4 -v all` / `size = "A4"` are accepted, and the
  names use lower case.
- `--paper aA4` and `--paper " a4"` are refused with exit 2 and the
  choices listed.
- A bad `size` together with `--list --paper a3` is reported, exit 1.
- `--suffix a4` at A3 gives `dan-overlay-a3-a4.pdf`, as OQ-7 allows.
- `--clean` with a bad `--paper` empties nothing, plain or `--json`.
- A minimal config with only `[paper] size = "a4"` gives
  `dan-overlay-a4.pdf`.

### New findings, not in the contract (minor, none blocking)

- **N-1 (nit).** A rejected `--paper` value is echoed lower-cased:
  `--paper aA4` reports "invalid choice: 'aa4'". This follows from
  lower-casing before argparse checks the choices. It is harmless.
- **N-2 (nit, UX).** A top-level `paper = "a4"`, the user's original
  wording, written in a file that has no `[paper]` table, fails with the
  older "…: [paper] should be a table" message. A pointer to
  `[paper] size = "a4"` would help someone who writes it the way it was
  first phrased. Owner: developer, if wanted.
