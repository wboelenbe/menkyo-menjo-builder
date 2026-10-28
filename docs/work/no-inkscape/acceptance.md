# Acceptance: no-inkscape (spike)

Work item: the `## Open` entry in DECISIONS.md, "A smaller package without
Inkscape?". The user asked: "can we optimize the package size by not using
inkscape? results do not need to be perfectly identical, as long as they look
good". The user then set the constraint: **pip-installable only, no system
dependencies at all** ("so that I can deploy anywhere"). That means wheels
only. No Inkscape, no Ghostscript, no cairo, pango, librsvg, poppler or
fontconfig, and no fonts installed on the system.

This is a **spike**. It changes nothing in `src/`, `tests/`, `pyproject.toml`
or the workflows. Its product is a decision the user can make from evidence:
which renderer, if any, replaces Inkscape, where the glyphs come from, and
what the real build will cost. This file is the evaluation contract. The
developer delivers what it lists, and the tester validates the spike against
it. A candidate is judged on the measurements below, not on anyone's opinion.

Baseline: HEAD `90e5799`. The `cli-only` item, running in parallel, removes
`src/gui.py`, `packaging/`, `web/`, `deploy/` and `src/menkyo/service.py`.
Nothing here depends on those files.

Revision 2 (this version) applies the user's decisions and the developer's
feedback recorded under `## Agreement`. Criterion IDs are kept stable.
Removed criteria and cases are listed as *removed* so that references to
them stay unambiguous.

## Platforms

| Platform | Status |
|---|---|
| macOS arm64 (the user's Mac) | **required** |
| Linux x86_64, glibc (Docker on a Synology NAS; portal image `linux/amd64`) | **required** |
| Linux arm64, glibc | nice to have: measured and reported, never a FAIL |
| Windows, musl/Alpine, Intel macOS | out |

Python 3.11, 3.12 and 3.13 on every required platform.

## Scope

**In**

- Every way of producing these outputs without system programs or system
  libraries, **for the variants `overlay` (inked text), `overlay-flat`
  (vector text) and `proof`, on white paper**:
  - the text-layer raster that `ink.py` grades;
  - the final PDF, inked and flat/proof;
  - the final PNG at `--dpi`.
- Where the glyphs come from when there is no fontconfig: Yuji Boku, which
  is vendored, and the crest-ring mincho, which today is the system font
  "Noto Serif CJK JP SemiBold". Also what happens to a character the font
  lacks, and to a font file that is missing.
- Whether the overlay PDFs' text is DeviceGray (criterion F-6).
- Measurements: visual similarity to Inkscape, PDF properties, file sizes,
  install footprint, time, memory, determinism, and wheel availability per
  platform.
- Licences of everything a candidate would add to the wheel's dependencies
  or to `src/menkyo/fonts/`.
- An effort estimate for the real build, including the tests, workflow and
  docs it would touch.

**Out**

- Any change to production code, tests, `pyproject.toml`, workflows, README
  or DECISIONS.md. The real build is a later `/feature` item, if the user
  says yes.
- The coloured variants (`full`, `full-cream`, `full-flat`), the drawn
  border, award colours, the paper tint and `--press` (`-K` / `-CMYK`,
  Ghostscript). The user will remove these in a later item (`plain-white`).
  The spike neither renders nor measures them.
- Changing what is drawn: layout, typeface choice, ink tuning. A candidate
  must reproduce today's design and not improve it. The one exception is
  DeviceGray colour in overlays (F-6), which is a wanted change.
- A physical print test (Q-4).
- Windows, musl and Intel macOS.
- The files the `cli-only` item removes.

## Two phases

- **Phase 1, for every candidate** listed under "Candidates to consider":
  desk research plus the cheap gates P-1 (wheel closure), P-2 (import and
  `ldd` / `otool -L` only) and P-4 (licences). A candidate that fails a gate
  is rejected with the failing ID and the evidence. The phase ends with one
  recommended route and at most one runner-up.
- **Phase 2, for the recommended route and at most one runner-up**: the
  prototype and every remaining criterion. Every other candidate gets a
  one-line reason in the candidate table and is not prototyped.
- `proto/` pins exact versions (`==`) for every package it installs, in a
  requirements file that the reproduce commands use.

## Deliverables

- **D-1 `docs/work/no-inkscape/spike.md`** contains:
  1. A candidate table: every candidate considered (at least those in
     "Candidates to consider"), with verdict *rejected*, *viable* or
     *recommended*, the phase it reached, and the **concrete reason** for
     each rejection (the failing criterion ID, a measured number, or a
     licence or wheel fact, each with its source).
  2. A results table for the recommended route and the runner-up against
     every criterion below: measured value, threshold, PASS or FAIL.
  3. A recommendation: one route for rendering and one for the crest glyph
     source. Alternatively, an explicit "no candidate meets the hard
     criteria", followed by the closest trade-off and what it would give up.
  4. Risks: what could still go wrong in the real build or in production.
     Include the effect on the `--json` contract, on `-f svg` output, on
     `--supersample`, on the regression and golden suites (which today fake
     `inkscape` and `gs`), on the "PDF embeds Yuji Boku" checks (F-3), on
     the dojo-portal image, and on the ordering with `plain-white` (Q-7).
  5. An effort estimate for the real build in developer-days, broken down
     by: the renderer module, the font handling, tests (golden and
     acceptance rework), the Docker test image, the workflow, and the docs
     (README, DECISIONS, `pyproject.toml` comment).
  6. A section **"For the user to judge"**: links to the comparison images
     with one line per case on what to look at, and a blank verdict column
     (acceptable, or not, with a note) for the user to fill in.
- **D-2 Comparison images** in `docs/work/no-inkscape/compare/`, as
  described under "Comparison images". Only stand-in data appears in them;
  see Personal data.
- **D-3 Prototype code** in `docs/work/no-inkscape/proto/` (or in the
  scratchpad, with the reproducible parts copied here). It never goes in
  `src/` or `tests/`. It must include:
  - the pinned requirements file;
  - a script that renders the cases below with the candidate;
  - a script that produces the Inkscape reference renders in Docker;
  - `compare.py`, which computes the metrics in G-1, G-3, G-5 and V-1 to
    V-4 and writes the comparison images;
  - a `README` paragraph at the top of the script, or a docstring, giving
    the exact commands to reproduce every number in spike.md.

  The prototype may import `menkyo.build_diploma.document()` and
  `menkyo.ink` to get today's SVG and grading. Monkeypatching them is fine.
  Editing them is not.
- **D-4 Measured numbers.** Every number in spike.md comes from a command in
  D-3 or from a quoted source (a PyPI page, a `pip download` or
  `uv pip compile` listing, or `docker image inspect`). Estimates are marked
  as estimates.

## Reference renders (the "Inkscape" side)

- Produce them in the Docker test image (`tests/docker/Dockerfile`, Debian
  bookworm, Inkscape 1.2.2) **with `fonts-noto-cjk-extra` added**.
- Why: in the plain test image, `fc-match "Noto Serif CJK JP SemiBold"`
  returns *DejaVu Sans*. The image installs `fonts-noto-cjk`, which has only
  Regular and Bold. SemiBold is in `fonts-noto-cjk-extra`, which the deploy
  image installs and the test image does not. Add it with a derived image in
  `proto/` or a one-off `docker run`. Record the face actually used: the
  crest PDF's `pdffonts` listing and the `fc-match` output. A candidate that
  matches the wrong reference face proves nothing.
- Every render pins `-c src/menkyo/example.toml` and passes `--name`,
  `--rank` and `--date` explicitly (as `''` where blank), so `[sample]` and
  `today` never decide the output. Runs on the Mac isolate `HOME` and
  `XDG_CONFIG_HOME`. Output goes to the scratchpad or
  `/private/tmp/claude-501/...`, never to `build/`.
- For V-3 and V-4, also keep the reference's intermediate text-layer PNG
  (the input to `ink_layer`) and its graded output. They are deleted with
  `build/.work/` unless the prototype intercepts them, for example by
  calling `_inked_text_image` from a driver or by copying from `.work`
  before cleanup.

## Cases

Each case is run by both Inkscape and the candidate with `-f pdf,png` at the
default 300 dpi, unless the row says otherwise.

| ID | argv after `-c src/menkyo/example.toml` | Why |
|---|---|---|
| C-1 | `-a dan -v overlay -n ヤン・ヤンセン -r 2 -d 2024-07-01` | inked text, transparent background, crest |
| C-2 | *removed* (full-cream: border, tint) | out of scope |
| C-3 | `-a shihan -v overlay -n ジョン・ドウ -r '' -d 2024-07-01` | licence as an overlay: no grade column, small kana ョ |
| C-4 | `-a dan -v overlay-flat -n アレクサンドル・ファン・デル・フェルデン -r 10 -d 2020-10-20` | vector text, shrunk long name, small kana ァ ェ, rotated ー, ・ |
| C-5 | `-a dan -v proof -n '' -r '' -d ''` | guides, dashed strokes, blank date grid |
| C-6 | *removed* (`--press`, `-K.pdf`) | out of scope |
| C-7 | *removed* (`--press`, `-CMYK.pdf`, coloured border) | out of scope |
| C-8 | C-1 with `--dpi 150 -f png` | `--dpi` honoured |
| C-9 | C-4 with a name containing at least one character **absent from Yuji Boku's cmap** (the developer finds one, e.g. by checking the CJK and kana a recipient name could use) | fallback or error, criterion G-4 |

The crest, including its ring lettering (`〇〇道場` on the lower arc and
`〇〇流柔術` on the upper), appears in C-1, C-3, C-4 and C-5 and is compared
as its own crop.

## Criteria

Thresholds are proposals from the tester, agreed with the developer under
`## Agreement`. **Hard** criteria must pass for a candidate to be
recommended. **Soft** criteria are measured and reported, and they decide
between candidates that pass the hard ones. A criterion that is hard only
on required platforms says so.

### Platform and licence (hard)

- **P-1 Wheels only, full closure.** Resolve the **full transitive
  closure** of the candidate's runtime dependencies (not `--no-deps`) with
  binary-only resolution, for Python 3.11, 3.12 and 3.13 on each platform:
  - `uv pip compile --only-binary :all: --python-version 3.1x --python-platform {aarch64-apple-darwin, x86_64-manylinux_2_28, aarch64-manylinux_2_28}`,
    or
  - `pip download --only-binary=:all: --python-version 3.1x` with the
    platform tags passed explicitly: `--platform macosx_11_0_arm64`, and for
    Linux every accepted manylinux tag (`manylinux_2_28_x86_64`,
    `manylinux_2_17_x86_64`, `manylinux2014_x86_64`, and the `aarch64`
    equivalents).

  The 6 combinations on required platforms must all succeed. The 3 Linux
  arm64 combinations are reported. Paste the resolved file names into
  spike.md. A pure-Python wheel (`py3-none-any`) counts.
- **P-2 Runs with no system libraries.**
  - **Linux:** a container `FROM python:3.13-slim-bookworm` with **only**
    `pip install` on top: no `apt-get install`, no fontconfig, no fonts.
    Required on `linux/amd64`; reported on `linux/arm64`. Phase 1: the
    candidate imports, and `ldd` on every native extension module and every
    bundled shared library shows **no `not found`**, and every resolved
    library is glibc (libc, libm, libpthread, libdl, librt), libstdc++,
    libgcc_s, `ld-linux*`, or a file inside the installed wheel (for example
    `*.libs/`). Phase 2: it renders C-1, C-3, C-4 and C-5 there.
    `dpkg -l | grep -Ei 'cairo|pango|rsvg|poppler|fontconfig|ghostscript|inkscape'`
    is empty in that container.
  - **macOS arm64:** natively, in a fresh venv. `otool -L` on every native
    extension module lists only `/usr/lib/libSystem*`, `/usr/lib/libc++*`,
    system frameworks that ship with macOS, or `@loader_path` / `@rpath`
    files inside the installed wheel. No Homebrew paths.
- **P-3 No silent system font lookups.** The candidate never reads system
  font directories, on Linux or on macOS (Hiragino, `/System/Library/Fonts`,
  `/Library/Fonts`, `~/Library/Fonts`). Every glyph comes from a font file
  the package ships or installs from PyPI. Proof:
  - the code path or option that disables system font loading, with the
    library's documentation or source quoted (for an outlines-before-render
    route: the output PDF has no `/Font` resources at all);
  - C-1 rendered in the P-2 container (no fonts) and in one with
    `fonts-noto-cjk` installed gives **pixel-identical** PNGs.
  - Soft, cross-platform: C-1's PNG on macOS arm64 against Linux x86_64
    differs by at most about 1 LSB: report max |Δ| per channel and the
    fraction of pixels with |Δ| > 1. A system-font substitution would show
    as a large regional difference, which is a FAIL of P-3.
- **P-4 Licences.** Every added dependency, every library bundled in its
  wheels, and every added font is compatible with distributing an MIT
  project's wheel: MIT, BSD, Apache-2.0, ISC, MPL-2.0, LGPL as a separately
  installed wheel, or OFL-1.1 for fonts. Explicitly accepted for libraries
  bundled in wheels: the FreeType licence (FTL, or GPLv2 by choice; we take
  FTL), libpng, zlib, and the IJG libjpeg licence. GPL and AGPL dependencies
  are rejected (PyMuPDF and Ghostscript are AGPL). For every vendored or
  subset font, **including the already vendored Yuji Boku**, state its
  Reserved Font Names and whether subsetting, instancing or converting to
  outlines triggers them. Name the OFL and `NOTICE` updates the real build
  needs.

### Glyphs and layout (hard)

- **G-1 Placement.** Measured on C-4 and C-5 only, flat renders at 600 dpi.
  For each glyph, crop its cell from both renders and find the offset by
  sub-pixel cross-correlation. Every glyph is within **0.15 mm** of the
  reference after global alignment. Report the worst glyph and its offset.
- **G-2 Vertical-text specifics are right.** A human check of the 600 dpi
  crops, confirmed by G-1:
  - small kana (ァ ェ ョ) sit upper-right in their cell;
  - ー is rotated 90° (vertical);
  - ・ is centred;
  - long-name shrink is the same size;
  - the date reads in kanji numerals.
- **G-3 Crest ring.** The ring lettering is a **mincho** (Noto Serif CJK JP
  SemiBold, or a stated equivalent such as Noto Serif JP instanced at
  wght 600, which the user accepts in "For the user to judge"), not Yuji
  Boku and not a sans. Measured on the V-2 crest crop (SSIM ≥ 0.95 and the
  region rule) **and** per ring glyph: centroid within **0.15 mm** of the
  reference. `traced_glyphs = true` (crest/*.svg paths) still renders; show
  it once with a throwaway traced glyph in a temp config dir.
- **G-4 Missing glyphs.** For a character absent from Yuji Boku (C-9):
  - report what Inkscape does today (fontconfig fallback to which face);
  - the candidate either falls back to a shipped face, or fails with a
    clear error naming the character and a non-zero exit. A blank or
    `.notdef` "tofu" box with exit 0 is a FAIL;
  - for the failure path, state where the check sits so that under
    `--json` the real build emits **exactly one `error` event** and no
    partial `done`. Demonstrate it if the prototype is driven through the
    CLI;
  - list the characters the example config and the three test names use
    that Yuji Boku lacks (this may be none).
- **G-5 Stroke weight.** The columns set at `font-weight` 500 and 600
  against a Regular-only Yuji Boku must match the reference's weight.
  - Find out whether bookworm's fontconfig (or Inkscape/cairo) synthetically
    emboldens those requests in the reference, with evidence (for example
    `FC_EMBOLDEN` in `fc-match -v`, or the glyph outlines in the PDF).
  - Find out whether today's flat PDF (C-4) carries Yuji Boku as a
    TrueType/CID font or as Type3 fonts or outlines (`pdffonts` type
    column), since emboldening can change that.
  - Ink coverage (sum of alpha) per column is within **±3 %** of the
    reference in C-4.
- **G-6 Missing font file.** If a font file the candidate needs (Yuji Boku
  or the crest mincho) is missing, unreadable or corrupt, the build stops
  with a clear error naming the file and a non-zero exit, and never falls
  back to a system font. Under `--json` the real build emits exactly one
  `error` event. The prototype demonstrates it by pointing at a missing
  path and at a truncated copy of the font.

### Visual similarity (hard, with the user's look as the final word)

Metric method, implemented in `compare.py`:

1. Rasterise both PDFs with **pdfium** (pypdfium2), at 150 dpi for the whole
   page and 600 dpi for crops. Also compare the PNGs each route writes
   directly.
2. Convert to greyscale over white. Overlay images are composited onto white
   first.
3. Align by sub-pixel translation (phase correlation or similar) and report
   the offset.
4. Compute the score.

- **V-1 Whole page, 150 dpi, PDF rasterised by pdfium.** SSIM (Gaussian
  window σ = 1.5; a numpy/scipy implementation is fine) is **≥ 0.98** for
  flat and proof (C-4, C-5) and **≥ 0.97** for inked (C-1, C-3). Mean
  absolute difference is **≤ 2.0 / 255**. The same scores on the directly
  written PNGs are **reported**, without a threshold.
- **V-2 Crops, 600 dpi.** SSIM is **≥ 0.95** on each crop:
  - heading (top three glyphs);
  - name column;
  - the rank 二段 / 十段 (where present);
  - date column bottom;
  - crest with ring.

  No crop may have a connected region larger than **0.3 mm²** with a
  difference over 64/255. Such a region would be a missing, extra or moved
  stroke. Anti-aliasing edges are kept out of this rule by sub-pixel
  alignment, or by a morphological opening of about **0.1 mm** on the
  difference mask before counting regions. State which is used.
- **V-3 Ink grading.** The candidate's text-layer raster (the input to
  `ink.ink_layer`) is compared with Inkscape's:
  - pixel size matches within 1 px on each side;
  - placement (x, y, w, h in mm) is within 0.05 mm, with the candidate's
    bbox taken from the outline bounds;
  - IoU of `alpha > 128` is **≥ 0.98**;
  - total alpha is within **±2 %**.

  After grading, compare the mean graded alpha over ink pixels (within
  **±0.01**) and the fraction of ink pixels with alpha < 0.9 × 255 (within
  **±2 percentage points**). The text-layer render keeps the 600 dpi
  default. `--supersample` 1 to 4 still works, or the spike says what
  becomes of it. Record the `--supersample 4` pixmap size (px) and the peak
  memory of that render.
- **V-4 Ink colour.** Ink `#111111` only. Measured on **solid interior
  pixels** of the un-composited text layer (alpha = 255 after eroding the
  mask by 2 px): median colour within **ΔE2000 ≤ 2** of the reference.
  Overlay PNGs keep a transparent background and proof PNGs are opaque
  white, as today.
- **V-5 "Looks good", operationally.** All of the following:
  - V-1 to V-4 pass, or each failure is shown in a crop and explained;
  - a reviewer (developer, then tester) finds none of these at 600 dpi:
    - a missing or substituted glyph;
    - a glyph in the wrong face;
    - wrong rotation;
    - a pale halo or ragged edge on the inked text (the failure DECISIONS.md
      describes);
    - jagged (unantialiased) edges;
    - a raster where the reference is vector;
  - **the user looks at the D-2 images and marks each case acceptable in
    spike.md "For the user to judge"**. The metrics only filter candidates.
    The user's verdict decides.

### PDF (hard unless marked)

- **F-1 Page size.** It is exactly A3 landscape, MediaBox
  1190.55 × 841.89 pt (±0.01), with one page and no rotation.
- **F-2 Vector stays vector.** The crest, rings and guides are vector
  paths. The flat and proof PDFs contain **zero** image XObjects. An inked
  PDF contains exactly **one** image, the text raster, with a soft mask
  (SMask) or an equivalent alpha. Show this by listing the XObjects with
  pikepdf or pypdf.
- **F-3 Text.** In the flat variants, text is either an embedded font
  (subset is fine; `pdffonts` shows `emb yes`) or vector outlines. Both are
  acceptable. Say which one is used. If it is outlines, the
  `pdffonts … | grep -i yuji` checks must change: in
  `tests/acceptance/test_ac_render.py`, `tests/acceptance/test_ac_wheel.py`
  and `.github/workflows/package.yml`. List them under effort. Whether text
  is searchable or copyable is reported (and goes to Q-6), not required.
- **F-4 Renders correctly elsewhere.** Every candidate PDF passes
  `qpdf --check` (or pikepdf's `Pdf.check()`, which runs the same checks)
  with no warnings, and rasterises in:
  - Ghostscript (in Docker);
  - poppler `pdftoppm` (in Docker);
  - pdfium;
  - macOS Preview/Quartz via `sips`.

  For each viewer at 150 dpi, against the candidate's own PNG composited on
  white: SSIM **≥ 0.95**, and the mean ink coverage (1 − L/255) over the
  text bbox within **±0.02**. The second number proves the soft mask is
  honoured (DECISIONS.md, "Ink density": the SMask is what silently breaks).
- **F-5 File size (soft).** Report it per case. Flag any PDF over **1.5×**
  the Inkscape PDF, or over 5 MB.
- **F-6 Overlay text is DeviceGray.** In the `overlay` and `overlay-flat`
  PDFs (C-1, C-3, C-4), all text is DeviceGray: vector text filled with
  `g` / `G` or a `/DeviceGray` colour space, and the inked raster an image
  in `/DeviceGray` with a `/DeviceGray` SMask, with no enclosing
  transparency group in `/DeviceRGB`. Check by a content-stream and
  resource walk (pikepdf) and by `gs -sDEVICE=inkcov` in Docker showing
  C = M = Y = 0.00000. PASS if the prototype's overlays are grey, **or** if
  spike.md states the concrete change that would make them grey and why it
  works. Report also the colour spaces of everything else on the overlay
  page (crest, rings) and on the proof page (not required to be grey). The
  user's rationale: grey overlays print pure black on any printer, with no
  separate press file.

### PNG

- **N-1 Pixel size (hard).** It is identical to Inkscape's at 300 dpi
  (expected 4961 × 3508) and at 150 dpi (C-8). The PNG embeds its dpi
  (pHYs), as Inkscape's does.
- **N-2 File size (soft).** Report it per case. Flag any PNG over **1.5×**
  the Inkscape PNG.

### Determinism (hard)

- **R-1 Same input, same output.** Running the same candidate command twice
  (C-1 and C-4, same machine) gives a byte-identical PNG, and PDFs that are
  identical apart from `/CreationDate`, `/ModDate`, `/ID` and the XMP dates.
  Show the diff method (for example pikepdf with those keys blanked, then a
  byte compare). Report also whether Inkscape is deterministic in the same
  sense, for context.

### Press

- **E-1 to E-5:** *removed*. `--press` goes away in `plain-white`. F-6
  replaces the need for a separate press file.

### Footprint, time, memory (soft, but they are the point of the item)

- **S-1 Install footprint.** Compare the summed wheel sizes (download, and
  installed size on disk) of the new dependencies plus any added font, per
  required platform, against the system packages they replace. Measure those
  in the reference image with `dpkg-query -W -f='${Installed-Size}'`,
  counting the closure that `apt-get install --no-install-recommends
  inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra` pulls into
  `python:3.13-slim-bookworm`. Report the same with `ghostscript` added, for
  reference, since `plain-white` removes it anyway. Report the `menkyo`
  wheel's own size before and after, since a vendored crest font changes it.
- **S-2 Slim Docker image.** `docker image inspect` sizes of two minimal
  runtime images, each `FROM python:3.13-slim-bookworm` (`linux/amd64`)
  with `pip install` of the menkyo wheel:
  - **before**: with the apt packages above (without ghostscript);
  - **after**: pip only.

  Target: after ≤ **40 %** of before. For scale, the test image with
  Inkscape is 1.54 GB on disk, and Inkscape plus fonts-noto-cjk alone are
  about 189 MB installed.
- **S-3 Render time.** Native arm64 only (Docker `linux/arm64` on the Mac,
  both routes in the same Docker, no emulation). Wall-clock per certificate
  for C-1 and C-4, the median of 3 runs. Reported as the ratio
  candidate / Inkscape. Target: ratio ≤ **1.25**. Also report the per-stage
  split (`text`, `ink`, `pdf`, `png`).
- **S-4 Peak memory.** One container per certificate, C-1 and C-4, peak
  memory read from cgroup v2 `memory.peak` at the end of the run
  (`/usr/bin/time` is not in slim). Target: candidate ≤ the Inkscape route,
  and ≤ **2 GB** either way (the portal runs one process per certificate).

### Compatibility of the real build (reported, not measured)

- **K-1** spike.md states, for the recommended route, whether these change,
  and how:
  - the CLI flags;
  - the `--json` events and stage keys (`text`, `ink`, `pdf`, `png`; `press`
    goes with `plain-white`) and the step totals;
  - `-f svg` output (the SVG plus its `-textlayer.png`), including whether
    it keeps `<text>` elements;
  - `--supersample` (its cap of 4 comes from cairo);
  - `--clean` and the `.fontconfig` cleanup;
  - `paths.require_tool`, `paths.tool_env` and `paths.system_font_dirs`;
  - the test fakes for `inkscape` and `gs` (`tests/fakes/fake_tool.py`) and
    the golden and regression assertions on tool calls;
  - the SVG files themselves. Keeping `document()` as the single source
    keeps the golden SVGs intact; any route that changes `document()` must
    say so.

  Any change is a user decision (CLAUDE.md), so each one goes to the open
  questions.

## Candidates to consider

At minimum, each of these needs a verdict and a reason (phase 1). The
developer may add others.

- **Leading hypothesis (test first).** Keep `document()`. Convert text to
  outlines with fontTools, from Yuji Boku and a vendored crest mincho (for
  example Google Fonts' Noto Serif JP instanced to wght 600, whole or
  subset). Write the PDF with a small SVG-subset-to-PDF writer of our own,
  or with pikepdf. pypdfium2 rasterises that PDF for the PNG and for the
  600 dpi text layer.
- **Runner-up to test:** resvg-py for the raster.
- **Rasterisers.**
  - resvg via a Python binding (for example `resvg-py`), text through its
    own fontdb from shipped font files;
  - skia-python: raster plus SkPDF, and its SVG module;
  - pypdfium2, rasterising a PDF the project writes itself, so a single
    drawing path feeds both outputs;
  - Pillow `ImageDraw` / `ImageFont` directly, with the libraqm and FreeType
    bundled in Pillow's wheels.
- **PDF writers.**
  - reportlab, alone or with svglib;
  - fpdf2;
  - pikepdf with hand-written content streams;
  - a small writer of our own;
  - skia-python's PDF backend.
- **Text to outlines.** fontTools converts each glyph to a path before any
  renderer sees the SVG. This removes the font-resolution problem for every
  renderer and can feed V-3's raster.
- **Crest glyph source.** One of:
  - vendor Noto Serif CJK JP SemiBold whole (state the size);
  - vendor Noto Serif JP (variable, Google Fonts) instanced to wght 600,
    whole or subset (state the size);
  - vendor a subset (to what coverage, given that `crest_ring` and `[art]`
    are arbitrary config, and how a character outside it is handled);
  - an OFL mincho available on PyPI;
  - subset at build time from a font the user supplies;
  - Yuji Boku (contradicts DECISIONS.md "The crest ring stays mincho", so
    it needs the user's consent).
- **Known non-starters**, to be confirmed with a one-line reason:
  - CairoSVG / cairocffi (system cairo);
  - rsvg-convert (system librsvg);
  - PyMuPDF (AGPL);
  - Ghostscript as a wheel (AGPL, and is there one?);
  - matplotlib (size).

## Comparison images (D-2)

- Per case, one **side-by-side** PNG: Inkscape on the left and the candidate
  on the right, each labelled, whole page at 100 dpi. One **crop sheet** at
  600 dpi with the V-2 crops in pairs, plus the same crops as a difference
  heat map (|Δ| scaled ×4).
- Committed images total **≤ 15 MB**, as PNG or high-quality JPEG. Full
  resolution stays in the scratchpad.
- An `index.md` in `compare/` (one line per image, saying what it shows) is
  fine. It is input to spike.md, not a separate report.

## Personal data

- Only `src/menkyo/example.toml` is used, with the stand-in names above
  (ヤン・ヤンセン, ジョン・ドウ and the long Dutch-style katakana name). It
  never reads `dojo.toml`, the per-user folder, `crest/` or `ref/`. The
  Docker build context guard already excludes them.
- No git operations by the developer or tester. The orchestrator commits.

## Test approach

The tester's VALIDATE pass is manual, except for re-running D-3:

1. Read spike.md and check that each criterion above has a measured value,
   a threshold and a verdict for the recommended route (and the runner-up,
   if any), and that each rejection carries a reason and its phase.
2. Re-run the D-3 commands with the pinned requirements, for at least C-1
   and C-4, and the P-1 resolution matrix. Metrics and PDF/PNG properties
   must reproduce exactly. Image and file sizes must reproduce within
   **1 %**. Time ratios must reproduce within **20 %**. A fresh P-2
   container (`linux/amd64`) must render C-1. R-1 is re-checked.
3. Inspect the D-2 images and do the V-5 reviewer check independently.
4. Confirm that `git status` shows changes from this item only under
   `docs/work/no-inkscape/` (the parallel `cli-only` item's changes are
   ignored).
5. Write `validation.md`. The spike PASSES when D-1 to D-4 are complete and
   reproducible. It does **not** require that a candidate passes. "None
   qualifies, here is why" is a valid result if it is measured.

No automated tests are added to `tests/` for this spike.

## Open questions

Answered by the user (see Agreement): Q-3 (`--press` goes, in
`plain-white`) and Q-5 (platforms).

Answered **after the spike, from its evidence** (the spike puts the numbers
next to each):

- **Q-1 Crest font.** Vendor Noto Serif CJK JP SemiBold whole, Noto Serif
  JP at wght 600 whole, or a subset? A subset is smaller but limits which
  kanji `crest_ring` and `[art]` may use. Is Noto Serif JP an acceptable
  equivalent if it looks right?
- **Q-2 Missing glyphs.** When a recipient's name contains a character Yuji
  Boku lacks, fall back to the shipped mincho (visibly a different face) or
  stop with an error?
- **Q-4 Print check.** Is the side-by-side on screen enough for the "looks
  good" verdict, or one real A3 print of C-1 from each route first?
- **Q-6 Compatibility.** If the recommended route changes `--supersample`,
  `-f svg`'s side raster or the `--json` step totals, is that acceptable for
  the portal? May flat-PDF text become outlines (not searchable, not
  copyable)? Must `-f svg` keep `<text>` elements, or may it carry outlines?

Still open for the user:

- **Q-7 Ordering with `plain-white`.** The spike only covers white-paper
  variants. If the real no-Inkscape build lands before `plain-white`, the
  coloured variants and `--press` would need a renderer too. Should the real
  build wait for `plain-white`? (Tester's recommendation: yes, so neither
  item builds for code the other removes.)

## Agreement

Revision 2, 2026-10-28. Recorded by the tester from the user's decisions and
the developer's feedback, as relayed and agreed by the orchestrator.

**User decisions**

1. Platforms: macOS arm64 and Linux x86_64 glibc are required; Python
   3.11–3.13; Linux arm64 nice to have; Windows, musl and Intel macOS out.
   Answers Q-5. Applied in "Platforms", P-1, P-2, S-2, S-3.
2. Plain white only. `full`, `full-cream`, `full-flat`, the border, award
   colours, paper tint and `--press` are removed in a later item
   (`plain-white`). The spike covers `overlay`, `overlay-flat` and `proof`.
   Answers Q-3. Removed: C-2, C-6, C-7, E-1 to E-5, the border crops (V-2),
   the corner-seam and moiré checks (V-5), and V-4 colours other than ink.
   C-3 is kept as an overlay case. Added: F-6 (overlay text DeviceGray).
3. Pip-only, no system dependencies at all: unchanged.

**Developer feedback, accepted**

- Two-phase spike; `proto/` pins exact versions. ("Two phases".)
- P-1: full transitive closure with explicit manylinux tags. P-2: the
  `not found` / allowed-library rule, and `otool -L` on macOS. P-3: no
  macOS system fonts either, plus a soft macOS-vs-Linux check within about
  1 LSB. P-4: FreeType/libpng/zlib/IJG accepted; Yuji Boku checked for a
  Reserved Font Name.
- G-1: per-glyph cell crops, sub-pixel cross-correlation, 0.15 mm, C-4 and
  C-5 only. G-3: the 0.5° rule is replaced by the V-2 crest crop plus a
  per-glyph centroid within 0.15 mm. G-4: one `error` event under `--json`
  on the failure path. G-5: investigate synthetic emboldening and Type3 /
  outlines in today's flat PDF.
- V-1: separate thresholds, pdfium-rasterised PDF ≥ 0.98 flat / ≥ 0.97
  inked; direct PNG reported. V-2: sub-pixel alignment or a ~0.1 mm opening
  on the diff mask. V-3: bbox from outline bounds; `--supersample 4` pixmap
  size and memory recorded. V-4: ink only, solid interior pixels of the
  un-composited text layer.
- F-3: outlines acceptable; the `pdffonts | grep yuji` checks would change.
  F-4: SSIM ≥ 0.95 at 150 dpi plus mean ink coverage in the text bbox
  within ±0.02; `qpdf --check` via pikepdf; viewers gs, poppler, pdfium,
  Preview via `sips`.
- S-3: native arm64 only, median of 3, candidate/Inkscape ratio; 20 %
  reproducibility tolerance on time and 1 % on image sizes. S-4: one
  container per certificate, cgroup v2 `memory.peak`.
- K-1: lists `paths.require_tool`, `tool_env`, `system_font_dirs`, the
  fakes and the golden tool-call assertions; keeping `document()` keeps the
  golden SVGs intact.
- Added R-1 (determinism) and G-6 (missing font file).
- The reference renders add `fonts-noto-cjk-extra` (tester's finding,
  confirmed).
- Q-1, Q-2, Q-4 and Q-6 are answered after the spike from its evidence; Q-6
  gains outlines/searchability and `-f svg` `<text>`.
- The developer's leading hypothesis and runner-up are listed first under
  "Candidates to consider".

**Tester's own changes in this revision**

- Measured cases for S-3 and S-4 moved from C-1/C-2 to C-1/C-4, since C-2
  is removed; this gives one inked and one flat case.
- S-1/S-2 "before" excludes Ghostscript (reported separately), so the
  footprint gain is not overstated by a tool `plain-white` removes anyway.
- Q-7 (ordering with `plain-white`) added.

**Disagreements:** none outstanding.
