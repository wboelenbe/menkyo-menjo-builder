# render-without-inkscape: validation

## Round 1

2026-10-29, tester. Working tree on top of `8509b85`, version 0.3.0.
Contract: acceptance.md including `## User approval (2026-10-29)`.

**Verdict: PASS.** Every AC passes. Three new findings outside the
contract are listed at the end; none blocks.

Every render pinned `-c src/menkyo/example.toml`, the example written by
`--example-config`, or a configuration made from it, with `HOME` and
`XDG_CONFIG_HOME` in a scratch directory. Only placeholder names were used.

### Suites (M-1)

- `uv run pytest -rs` on the Mac: **542 passed, 0 skipped** (4 min 8 s).
  No `render` test skipped.
- `scripts/test-docker.sh -rs`: **538 passed, 4 skipped** (4 min 14 s).
  All four skips are 'no git history in the image'
  (`test_ac_cli_only.py:50`, `:302`, `test_ac_render_without_inkscape.py:256`,
  `:1065`). None is a `render` test.
- After the Q-7 change below: `tests/regression` passes on the Mac (33 golden
  tests) and in a freshly built `menkyo-test` image (125 passed).
- Test image: `menkyo-test` 941 MB (`du -sx /` 685 MB), against 1.44 GB
  before.

### Q-7: flat and proof PDF hashes pinned (tester)

- New file `tests/regression/golden/pdf_sha256.json`: a note on fontTools
  bumps, the fontTools version (4.68.0), and the sha256 per case of every
  `-overlay-flat` and `-proof` PDF. That is 8 PDFs: `inked` ×6 and
  `flat-pdf` ×2.
- `make_golden.py --pdf-hashes` rewrites only that file. `manifest.json` is
  untouched (AC-25), as `git status` confirms.
- `test_output_matches_baseline` asserts the PDF bytes.
  `test_pdf_hashes_cover_known_cases` guards the file.
- A mutated hash fails with the note in the message. Recorded under 'Test
  changes' in acceptance.md.
- The same hashes pass in the Linux arm64 image, so the flat and proof PDFs
  are byte-identical on macOS arm64 and Linux arm64.
- Follow-up for the docs agent (not an AC failure): `tests/README.md` could
  mention `pdf_sha256.json` and `--pdf-hashes`.

### Per AC

| AC | result | evidence |
|---|---|---|
| AC-1 | PASS | `test_ac1_*` pass on both platforms. The installed wheel runs with `PATH` = venv `bin` + `/usr/bin:/bin`. M-3: the slim amd64 image has no inkscape, fontconfig, fonts-noto, poppler, ghostscript or cairo (the dpkg grep is empty). |
| AC-2 | PASS | `test_ac2_*`. Wheel `Requires-Dist`: `fonttools>=4.68`, `numpy>=1.22`, `pillow>=9.0`, `pypdfium2==5.14.0`, `scipy>=1.8`. `uv lock --check` passes. |
| AC-3 | PASS | `test_ac3_*`. The wheel holds both fonts, `OFL.txt` and `OFL-NotoSerifJP.txt` (also under `dist-info/licenses/`). |
| AC-4 | PASS | `test_ac4_*`. No `.fontconfig` or `.work` after any manual run. |
| AC-5–AC-8b | PASS | The tests pass. By hand: `-f svg` and `-f png` with `-n 𠮷田` exit 1 with nothing written, and under `--json` there is one `error` event. `--clean` with a glyph error or with `--dpi 0` keeps `old.txt`. |
| AC-9 | PASS | The tests pass. By hand: a relative arc `a` is refused, naming `crest/한.svg`, also under `--json` and on `overlay`. A traced glyph using `C S Q T h v` and relative commands renders. |
| AC-10 | PASS | The tests pass. |
| AC-11 | PASS | Tests. M-4: `qpdf --check` (11.3.0) says 'No syntax or stream encoding errors' and pikepdf 10.17 `check_pdf_syntax()` returns `[]`, for C-1, C-3, C-4 and C-5. |
| AC-12 | PASS | Tests. On the amd64 files: 0 font objects, 0 text operators. C-4 has 8078 path operators. |
| AC-13 | PASS | Tests. amd64 C-1: one `/DeviceGray` image with a `/DeviceGray` SMask. C-4: no image. |
| AC-14 | PASS | Tests. M-5: `gs -sDEVICE=inkcov` gives C-1 `0.00000 0.00000 0.00000 0.03243`, C-4 `0.00000 0.00000 0.00000 0.03882`. Today's C-1 gives `0.04152 0.04249 0.04249 0.03251`. |
| AC-15 | PASS | `test_ac15_deterministic` passes. M-3, macOS arm64 against Linux x86_64 (emulated, same pinned versions): C-1 and C-4 **PDFs and PNGs are byte-identical** (PNG max \|Δ\| 0). |
| AC-16 | PASS | See M-4 below: every viewer with anti-aliasing has SSIM ≥ 0.976 and coverage within ±0.008. Without anti-aliasing see new finding F-1. |
| AC-17 | PASS | Tests. By hand with `-f png --all`: overlay and flat are LA, the proof RGBA, all 4961 × 3508 with corner alpha 0. `--dpi 1` gives 17 × 12 at 0.99 dpi; `--dpi 7` gives 116 × 82. |
| AC-18 | PASS | PDF at 150 dpi: SSIM 0.99972–0.99974, MAD 0.041–0.059, offset ≤ 0.01 px. PNG: SSIM 0.99865 (C-8) to 0.99996, MAD ≤ 0.271. |
| AC-19 | PASS | Every column and crest: SSIM ≥ 0.9994, largest difference region 0.000 mm², ink −0.06 % to +0.05 %. |
| AC-20 | PASS | Glyph cells: worst 0.0014 mm (ス, formula; C-4, C-4b, C-5). Crest ring: worst 0.0037 mm (場, every case). |
| AC-21 | PASS | C-1 7299 × 3733, IoU 0.9962, alpha +0.06 %. C-3 7305 × 3733, IoU 0.9961, alpha +0.04 %. |
| AC-22 | PASS | M-2 below. |
| AC-23 | PASS | Tests. The installed wheel's `--json` events run text → ink → pdf → png, then `file` and `done`. Any failure ends in one `error` event with exit 1. |
| AC-24 | PASS | `test_ac24_*`. |
| AC-25 | PASS | `tests/regression` passes. The manifest is unchanged. |
| AC-26 | PASS | Medians are C-1 189 MB, C-1p 189, C-4 64, C-4p 58 and C-5 64. Process guard on the Mac: C-1 359 MB (≤ 400), C-4 77 MB (≤ 160). |
| AC-27 | PASS | C-1 2.51 s against today's 3.65 s. C-4 0.34 s against a limit of 0.85 s (1.1 × 0.776). C-5 0.38 s against a limit of 0.84 s. |
| AC-28 | PASS | The wheel is 10.53 MB. Its payload is only `menkyo/` (14 files). |
| AC-29 | PASS | Automated test passes on both platforms. Manual run on the Mac (venv in scratch, run from scratch) and M-3 (amd64) both pass. |
| AC-30 | PASS | M-6: all six resolve (3.11: numpy 2.4.6, scipy 1.17.1; 3.12/3.13: numpy 2.5.4, scipy 1.18.1; fonttools 4.68.0, pillow 13.0.0, pypdfium2 5.14.0). `uv sync --frozen` works. It also removed an extraneous `typing-inspection` from the project `.venv`, which was not in the lock. |
| AC-31 | PASS | `-rs` shows no skip on the Mac. `test_ac31_*`. |
| AC-32 | PASS | `test_ac32_*`. Image size above. |
| AC-33 | PASS | `test_ac33_workflow`. |
| AC-34–36 | PASS | Tests. I read the DECISIONS entry: it overrides the right entries, records the family mapping and the figures, and the Open items are as required. |
| AC-37 | PASS | 0.3.0 in `pyproject.toml`, in `menkyo --version` and in the wheel name. |
| AC-38 | PASS | The whole suite passes on both platforms. |

### M-1: memory and time (`measure.sh`, native arm64 Docker, today then new, back to back)

| case | today (8509b85, Inkscape) | new | limit |
|---|---|---|---|
| C-1 | 412 MB, 3.65 s | **189 MB, 2.51 s** | ≤ 320 MB, ≤ 3.65 s |
| C-1p | 413 MB, 3.07 s | **189 MB, 2.34 s** | ≤ 320 MB |
| C-4 | 124 MB, 0.78 s | **64 MB, 0.34 s** | ≤ 110 MB, ≤ 0.85 s |
| C-4p | 103 MB, 0.38 s | **58 MB, 0.22 s** | ≤ 110 MB |
| C-5 | 102 MB, 0.77 s | **64 MB, 0.38 s** | ≤ 150 MB, ≤ 0.84 s |

- Single runs, new: C-1 290 / 188 / 189 (the first run is cold). Today:
  C-1 762 / 412 / 412 and C-4 124 / 141 / 104, cold runs again.
- C-1 is 20 % of the original 933 MB.
- DECISIONS gives C-1 206 MB and C-4 64 MB. My medians are within its
  figures or below them.
- C-1 stage split (new, median of 3, from the arrival times of the `--json`
  events): start and checks 0.08 s, text 0.18 s, ink 1.69 s, PDF 0.23 s,
  PNG 0.16 s, files and done 0.16 s.

### M-2: comparison sheets (`compare/`, 4.3 MB)

- `<case>-page.png` for C-1, C-3, C-4, C-4b, C-5 and C-8: today | new |
  \|Δ\| × 4. They are 100 dpi, except C-8, which is its 150 dpi PNG.
- `<case>-crops600.png`: name, rank, date, heading and crest at 600 dpi.
- `traced-crest-crops600.png`: a synthetic traced 한, rendered by 8509b85
  with Inkscape and by the new code. SSIM 1.0000, MAD 0.035, ink −0.01 %.

I looked at every sheet, and at 1:1 details of the C-1 name (inked), the
C-4b name and the traced glyph:

- No missing, substituted or wrongly rotated glyph.
- ァ ェ ョ sit upper right, ー is vertical, ・ is centred, and the shrunk
  C-4 name is the same size. The date is in kanji, and C-5's date grid is
  blank.
- Inked edges are as today's: no halo, no ragged edge. Vector stays vector.
- The \|Δ\| panels show only hairline anti-aliasing edges. The crest ring
  characters show faintly, from the Noto Serif JP face against CJK JP.
- The traced glyph comes out tiny in both versions. That is how a 1000-unit
  viewBox scales at 8509b85; nothing changed.

### M-3: Linux x86_64

- Feasible under emulation: `docker run --platform linux/amd64
  python:3.13-slim-bookworm`, `uname -m` says `x86_64`, about 13 s in all.
- `pip install -c c.txt` of the wheel, with `c.txt` from `uv export
  --no-dev --no-hashes`, installed fonttools 4.68.0, numpy 2.5.4, pillow
  13.0.0, pypdfium2 5.14.0 and scipy 1.18.1, as on the Mac.
- The dpkg grep is empty.
- C-1 and C-4 render from `/tmp` and end in `done`.
- AC-11, AC-12 and AC-14 checks: one page; MediaBox
  `[0 0 1190.5512 841.8898]`; `%PDF-1.4` … `%%EOF`; `xref_problems` `[]`;
  no fonts and no text operators; colour operators only `g`/`G`; no
  transparency group. pdfium opens both.
- All four files are byte-identical to the Mac's.

### M-4: viewers (150 dpi, against the package's own PNG on white, halved)

| case | gs, anti-aliased | poppler 22.12 | Quartz (`sips`) | gs, no anti-aliasing (default `pnggray`) |
|---|---|---|---|---|
| C-1 | 0.9968, +0.0012 | 0.9978, +0.0003 | 0.9783, −0.0003 | 0.9951, +0.0049 |
| C-3 | 0.9976, +0.0014 | 0.9985, +0.0004 | 0.9808, −0.0002 | 0.9956, +0.0055 |
| C-4 | 0.9983, +0.0071 | 0.9991, +0.0022 | 0.9902, −0.0001 | 0.9800, **+0.0281** |
| C-5 | 0.9977, +0.0076 | 0.9976, +0.0025 | 0.9881, +0.0000 | 0.9761, **+0.0298** |

Each cell is SSIM, then the coverage difference over the text columns.
Ghostscript is 10.00.0.

- The contract compares as a viewer shows the page, which is with
  anti-aliasing. On that reading every viewer passes (SSIM ≥ 0.95, coverage
  ±0.02), and the inked overlays' soft mask is honoured everywhere.
- gs's default device has no anti-aliasing, and there the flat cases are
  just over ±0.02. See F-1.

### Edge cases (beyond the tests)

| case | result |
|---|---|
| `--dpi 0`, `-5`, `2401` with `-f png` | exit 1 with `--dpi N: use a resolution from 1 to 2400`, and one `error` under `--json`. No traceback (R-2 is fixed). |
| `--dpi 1`, `--dpi 7` | Valid PNGs. |
| `--dpi 0` with `-f pdf` or `--list` | Exit 1. 8509b85 accepted both, exit 0: F-2. |
| Missing glyph from `--name`, `--rank`, `--honorific`, `[sample] name`, config keys | Each source is named (tests, plus `-f svg` and `-f png` by hand). |
| U+FE0F (variation selector), tab, newline in `--name` | Refused as missing glyphs, naming U+FE0F / U+0009 / U+000A. The tab and newline are echoed raw in the message: F-3. |
| Half-width ｱｲ, Latin `John Doe`, `--suffix 😀` | Render. The suffix only goes into file names. |
| Traced crest with `A` or `a` | Refused, naming the file, on `-f pdf`, on overlay and under `--json`. It is also refused on `-f svg` (see F-2's note). |
| Traced crest with `<ellipse>`, `<g transform>`, `style=` | Renders and draws only the `<path d>` data. This is unchanged from 8509b85: `_traced_glyph`'s regex has always taken only `<path d="…">`. |
| Traced file that is not XML / has no viewBox | Treated as absent, so the ring character needs the font, and 한 is reported missing from Noto Serif JP. Unchanged from 8509b85. |
| Truncated or missing font | Tests (AC-10). |
| PNG-only and SVG-only, `--all` | 15/6 progress events, 9/12 `file`, 1 `done`, no `.work`. The SVG-only run writes the three `-textlayer.png`, as before. |
| `--clean` with an error before writing (glyph, `--dpi`) | The directory is kept. |

### New findings, not in the contract

- **F-1, minor, for the print test.** The flat PDFs are now outlines, so
  Ghostscript without anti-aliasing (its default raster devices; also the
  CUPS route to a non-PostScript printer on Linux) fattens them more than
  it did today's font text.
  - At 150 dpi: coverage +0.028 (C-4) and +0.030 (C-5), against +0.003 and
    +0.005 for today's PDFs on the same device.
  - At 600 dpi against today's PDF: C-4's shrunk name has **+9.0 % ink**,
    its formula +2.2 % and the crest +2.6 %. C-1 is unchanged (an image).
  - Quartz, poppler, pdfium and anti-aliased gs show no such effect.
  - Only the user's print path decides whether this matters. Printing from
    macOS goes through Quartz. Worth knowing for the ongoing print tests;
    no code change suggested yet.
- **F-2, minor, compatibility.** The `--dpi` range check (R-2's fix) runs
  for every run, before `--list`.
  - `menkyo --list --dpi 0` and `-f pdf --dpi 0` exited 0 at 8509b85 and
    now exit 1.
  - Suggested: check the range only when a PNG will be written and not
    under `--list`.
  - In the same vein, a traced crest with an arc is refused for `-f svg`
    too, which 8509b85 wrote. The contract's AC-9 only requires refusal for
    the PDF.
- **F-3, nit.** A control character in a name (tab, newline) is reported as
  a missing glyph, which is reasonable. But the message prints the raw
  character, so the newline breaks the line. The `U+000A` code is there.
  Showing only the code for characters below U+0020 would read better.
