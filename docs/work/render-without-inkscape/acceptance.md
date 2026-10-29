# render-without-inkscape: acceptance

Work item: replace Inkscape with the pip-only renderer that the no-inkscape
spike recommended and the user accepted ([spike.md](../no-inkscape/spike.md),
"User decisions"; DECISIONS.md `## Open`, "Render without Inkscape"). Glyph
outlines come from fontTools, our own writer turns the SVG subset into a PDF,
and pypdfium2 draws the PNG and the 600 dpi text layer.

Baseline: `8509b85`, the last commit rendered by Inkscape. "Today" below
means that commit, rendered in the reference image described under
"Reference".

## User decisions (not reopened here)

- Route: fontTools text-to-outlines, our own SVG-subset-to-PDF writer,
  pypdfium2 for the PNG and the 600 dpi text layer. `document()` stays the
  single source of the drawing.
- Crest font: Noto Serif JP SemiBold (noto-cjk `Serif2.003`,
  `SubsetOTF/JP/NotoSerifJP-SemiBold.otf`), vendored whole (+5.4 MB).
- A character missing from the fonts is an error, checked up front before
  any rendering, with a message asking for a replacement character. Under
  `--json` it is one `error` event. There is no fallback.
- PDF text is outlines and not searchable. Overlay PDFs are DeviceGray.
- The bar is "looks good", not identical. The user's print tests are
  ongoing.
- Platforms: macOS arm64 and Linux x86_64 (Synology NAS). pip-installable,
  with no system dependency at runtime: no Inkscape, no Ghostscript, no
  fontconfig, no apt fonts.
- The flat variants render in greyscale to cut their peak memory. Whole-run
  memory is measured, with C-1 targeting roughly a third of the original
  933 MB.
- `--supersample` no longer exists. The CLI flags and the `--json` events
  stay backwards compatible (stages `text`, `ink`, `pdf`, `png`).
- The Docker test image becomes slim, and `scripts/test-docker.sh` stays the
  Linux gate. `render` tests also run on the Mac.
- Version: the user decides (Q-1).

## Scope

**In**

- A renderer module in `src/menkyo/`, replacing `_inked_text_image`'s
  Inkscape calls, `render()`'s Inkscape calls and `_font_env()`.
- The vendored crest font, its licence, `NOTICE`, `pyproject.toml`
  (dependencies, licence files, comments, pytest markers) and `uv.lock`.
- The up-front glyph check, and the missing or corrupt font-file errors.
- Greyscale rendering for `overlay-flat` and the overlay's page raster.
  `proof` stays colour, because its guides are coloured (see AC-14).
- Removing what only Inkscape needed: `paths.find_tool`, `require_tool`,
  `tool_env`, `system_font_dirs`, `_EXTRA_BIN`, `_INSTALL_HINT`,
  `build_diploma._font_env`, the `.fontconfig` directory and its clean-up,
  and the `subprocess` calls.
- Tests: the new acceptance tests, the reference fixtures, the migration of
  the existing suite (tester; see "Changes to the existing suite"),
  `tests/docker/Dockerfile`, `scripts/test-docker.sh` and
  `.github/workflows/package.yml`.
- README, DECISIONS.md (new entry, Open item closed, house-style sweep item
  added), NOTICE and `tests/README.md`, written by the `docs` agent in the
  user's house style (British English, sentence-case headings, ‘single
  quotes’, spaced en dash, no serial comma). The tests check substance, not
  wording or dash style.
- `ink.py` outside the grading (Agreement 1): reading the coverage without
  the RGBA round trip, importing scipy lazily. The graded alpha stays bit
  for bit.

**Out**

- Any change to what is drawn. Layout, `document()`, typography, the ink
  tuning and `INK_DPI` stay as they are. The only visible differences allowed
  are the renderer's own (anti-aliasing, the crest face Noto Serif **JP**
  against today's Noto Serif **CJK JP**, both SemiBold) within the
  thresholds below.
- `-f svg` with outlines. The SVG keeps its `<text>` elements, as today.
- A fallback face for missing glyphs.
- Searchable PDF text, ToUnicode maps, PDF/A.
- The physical print test (the user's, ongoing).
- dojo-portal. Its image can drop `inkscape fontconfig fonts-noto-cjk
  fonts-noto-cjk-extra` once it takes the new wheel; that change belongs to
  the portal repository.
- Linux arm64, Windows, musl and Intel macOS. These are not required; Linux
  arm64 is the native Docker on the Mac and is used for measurements.
- `CLAUDE.md`. Its line "Inkscape renders. It is not installed on the Mac…"
  goes stale; the orchestrator updates it at commit time (Q-5).
- A4, kyū grades and the Dutch companion sheet (other Open items).

## Reference: today's Inkscape output

Kept in `tests/acceptance/render_without_inkscape/`:

| file | what |
|---|---|
| `make_reference.sh` | `git archive 8509b85 src/menkyo` into a temporary directory, mounted read-only into `Dockerfile.ref`. Renders the cases and writes `reference/`. Needs Docker only. |
| `Dockerfile.ref` | `python:3.13-slim-bookworm` with `inkscape fontconfig fonts-noto-cjk fonts-noto-cjk-extra`. The plain test image lacks `-extra`: there, `fc-match "Noto Serif CJK JP SemiBold"` answers *DejaVu Sans*, so its crest ring is a fallback face and no reference at all. |
| `ref_render.py` | runs 8509b85's own `main()` per case, keeps the text layer and its `<image>` element, and reduces the output with `refkit` |
| `refkit.py` | the case list, pdfium rasterising (grey on white, `round(pt × dpi / 72)` px), SSIM, alignment, crops, and a small PDF reader (objects, xref check, colour operators, images, fonts). The same code on both sides of every comparison. |
| `measure.sh` | whole-run cgroup `memory.peak` and wall time, one fresh container per run |
| `reference/` (4.3 MB) | per case: `<case>-pdf150.png` (the PDF at 150 dpi), `<case>-png.png` (the PNG as written, on white, halved by `refkit.half` when it was 300 dpi), `<case>-<column>.png` (600 dpi crops of every text column and the crest), `C-1`/`C-3-textlayer-graded.png` (graded text-layer alpha), `meta.json` (boxes, glyph cells, ring positions, sizes, PDF/PNG facts, toolchain) |

Rendered on 2026-10-29 at `8509b85`, `linux/arm64` (OrbStack on the Mac).
Inkscape 1.2.2. Crest face `NotoSerifCJK-SemiBold.ttc: "Noto Serif CJK JP"
"SemiBold"`. pypdfium2 5.14.0 for the rasters. Only `example.toml` and the
stand-in names below appear.

Today's output (from `meta.json`):

- Every PDF is one page with MediaBox `[0 0 1190.551181 841.889764]`, a
  `/DeviceRGB` transparency group, `rg`/`RG` colour operators, embedded
  fonts (3 font objects in the inked overlays for the crest, 6 in the flat
  and proof PDFs) and text operators.
- The inked overlays (C-1, C-3) hold one `/DeviceGray` image with a
  `/DeviceGray` SMask. The flat and proof PDFs hold no image.
- PDF sizes: C-1 789 KB, C-3 754 KB, C-4 75 KB, C-5 72 KB.
- Every PNG is RGBA, 4961 × 3508 at 300 dpi (C-8: 2480 × 1754 at 150),
  pHYs 299.999 dpi, and **transparent, the proof included** (corner
  alpha 0).
- The C-1 text layer is 7299 × 3733 px at `<image x="51.6869" y="68.6057"
  width="308.9884" height="158.0168">`. C-3's is 7305 × 3733.

## Cases

argv after `-c src/menkyo/example.toml` (`refkit.CASES`; the spike's IDs):

| ID | argv | why |
|---|---|---|
| C-1 | `-a dan -v overlay -n ヤン・ヤンセン -r 2 -d 2024-07-01 -f pdf,png` | inked text, crest |
| C-3 | `-a shihan -v overlay -n ジョン・ドウ -r '' -d 2024-07-01 -f pdf,png` | licence, no grade column, small ョ |
| C-4 | `-a dan -v overlay-flat -n アレクサンドル・ファン・デル・フェルデン -r 10 -d 2020-10-20 -f pdf,png` | vector text, shrunk name, ァ ェ ・ |
| C-4b | as C-4 with `-n ピーター・ファン・デル・フェルデン` | ー turned vertical |
| C-5 | `-a dan -v proof -n '' -r '' -d '' -f pdf,png` | coloured dashed guides, blank date grid |
| C-8 | C-1 with `-f png --dpi 150` | `--dpi` |

Missing-glyph characters, checked with fontTools 4.68 against the two font
files:

| character | Yuji Boku | Noto Serif JP SemiBold | used for |
|---|---|---|---|
| 𠮷 U+20BB7 | no | yes | the body face lacks it (name, rank, `[art]`) |
| ㇰ U+31F0 (small katakana ku) | no | yes | a plausible name character the body face lacks |
| 한 U+D55C | no | no | the crest face lacks it (`crest_ring`) |
| 😀 U+1F600 | no | no | `--honorific`, `[motto]` |
| U+3000 ideographic space, `/`, `:` | yes | yes | must keep working in a name |

## Acceptance criteria

Thresholds for the visual criteria are the spike's, which the user accepted
with the comparison images. Every render pins `-c src/menkyo/example.toml`
or a configuration the test writes, and isolates `HOME` and
`XDG_CONFIG_HOME`.

### Renderer and package

- **AC-1 No external program, no system font.**
  - A run of C-1 and C-4 succeeds with `PATH` set to an empty directory.
  - No file in `src/menkyo/` mentions `inkscape` or `fontconfig`
    (case-insensitive), or imports `subprocess`.
  - The SVG keeps `font-family="Yuji Boku"` and `font-family="Noto Serif
    CJK JP SemiBold"` byte for byte (the goldens). The writer maps those
    family names to the vendored files (the crest family to
    `NotoSerifJP-SemiBold.otf`), and DECISIONS records the mapping.
  - Fonts are opened from the package's files, never by family name. C-4
    rendered with `FONTCONFIG_FILE` and `FONTCONFIG_PATH` pointing at
    nonsense, and a decoy `YujiBoku-Regular.ttf` (really another face) under
    `$HOME/.fonts`, `$HOME/Library/Fonts` and `$XDG_DATA_HOME/fonts`, gives a
    PDF byte-identical to a plain run.
- **AC-2 Dependencies.** `[project] dependencies` are exactly `pillow`,
  `numpy`, `scipy`, `fonttools` and `pypdfium2`. `pypdfium2` is pinned with
  `==`, because its raster bytes move between releases (spike, risk 5).
  `fonttools` has a lower bound. The wheel's `Requires-Dist` says the same.
  `uv lock --check` passes. The "system programs it also needs" comment in
  `pyproject.toml` is gone, or says there are none.
- **AC-3 Fonts shipped.**
  - `src/menkyo/fonts/YujiBoku-Regular.ttf` is unchanged.
  - `src/menkyo/fonts/NotoSerifJP-SemiBold.otf` has sha256
    `116d06c2b11ceba33ccb3f8c9eb1c86aba3d5761a1199fd37f74e83365e7a53d`,
    the noto-cjk `Serif2.003` file unmodified.
  - A licence file for it sits in `src/menkyo/fonts/` (any name other than
    `OFL.txt`) and contains "SIL Open Font License". It is listed in
    `license-files`, so it reaches the wheel's `dist-info/licenses/`.
  - `NOTICE` has a section for Noto Serif JP: OFL-1.1, its copyright from
    the font's name table, and where it came from (noto-cjk `Serif2.003`).
    The README's "Licence" section says "the bundled fonts" where it said
    "the bundled font".
- **AC-4 Inkscape-only code removed.** `paths` has no `find_tool`,
  `require_tool`, `tool_env`, `system_font_dirs`, `_EXTRA_BIN` or
  `_INSTALL_HINT`. `build_diploma` has no `_font_env`. No run leaves a
  `.fontconfig` directory in `--out`. `paths.checkout_root`, `resource`,
  `user_data_dir` and `default_output_dir` stay as they are.

### Missing glyphs (user decision: an error, up front)

The fonts are Yuji Boku for every printed column and Noto Serif JP SemiBold
for the crest ring. The ring carries `[dojo] crest_ring` on the lower arc
and `[art] name` on the upper. Every run that writes files is checked,
`-f svg` included. `--list` is not checked (AC-9).

What is checked is exactly what will be drawn (Agreement 5):

- only the selected awards (`-a`), and only strings that actually appear;
- the honorific only when a name is printed;
- a `[sample] rank` only on documents with a grade column, an explicit
  `--rank` always;
- `[art] name` against Yuji Boku (its column) and the crest font (the
  ring);
- a ring character with a traced `crest/<ch>.svg` is not checked against
  the crest font.

The message names the source for fill-ins from the configuration too: for
example "`[sample] name` (no `--name` given)", `[sample] rank`, and
`[recipient] honorific`. As a backstop, the writer raises the same error if
it meets a character missing from a cmap; it never draws `.notdef`.

- **AC-5 A fill-in flag, plain output.** `--name 𠮷田`, `--name ㇰロ`,
  `--rank 𠮷段` (a literal rank) and `--honorific 😀` each end the run with:
  - exit code 1, empty stdout, no traceback;
  - a message on stderr naming the character, its code point as `U+XXXX`
    (for example `U+20BB7`), and the flag it came from (`--name`,
    `--rank`, `--honorific`), and asking for a replacement character (the
    word "replace" appears);
  - no file written and no `.work` left in `--out`, which holds exactly what
    it held before.
- **AC-6 The same under `--json`.** stdout is exactly one line,
  `{"event": "error", "message": …}`, carrying the same message. There is no
  `progress`, `file` or `done` event, and the exit code is 1.
- **AC-7 Configuration strings.** A configuration written by the test with
  one bad character in one key fails the same way. The message names the
  character, its `U+` code and the key:
  - `[art] name` with 𠮷 (it sits on the crest ring, but Yuji Boku lacks it);
  - `[dojo] name`, `[signer] title`, `[signer] name`, `[motto] text`, and an
    award's `heading` or `formula`, each with 𠮷;
  - `[dojo] crest_ring` with 한, which the crest font lacks;
  - `[motto] text` with 😀.
- **AC-8 Up front, for the whole run.**
  - With `-a all` and the bad character only in the third award's `heading`,
    nothing is written for the first two either.
  - With `--clean`, a pre-existing file in `--out` is still there after the
    error. The check runs before the directory is emptied.
- **AC-8b Scope** (tests `test_ac5_sample_name_is_named_by_its_key`,
  `…_sample_rank_only_where_a_grade_is_drawn`, `…_honorific_only_with_a_name`,
  `…_only_the_selected_awards_are_checked`). As the scope rules above: a bad
  `[sample] name` fails and is named as such; a bad `[sample] rank` passes on
  a licence, fails on dan as `[sample] rank`, and a bad explicit `--rank`
  fails on a licence; a bad config honorific passes without a name and fails
  with one; a bad heading on an award not selected passes.
- **AC-9 Not errors.**
  - `--list` with a missing character lists as before, exit 0.
  - A name with U+3000, `/` and `:` (`ヤン　ヤンセン/x:y`) renders.
  - With `traced_glyphs = true` and a traced `crest/한.svg` beside the
    configuration, `crest_ring = "한〇道場"` renders, because the traced
    glyph stands in for the font. A character with no traced file still
    needs the font.
  - But a traced file whose path uses a command the writer refuses fails
    (Agreement 6). The writer takes `M L H V C S Q T Z`, absolute and
    relative, and refuses the arc `A`. Exit 1; the message names the crest
    file; under `--json` one `error`; no PDF, no `.work`
    (`test_ac9_traced_glyph_with_an_arc_is_refused`).
- **AC-10 Missing or corrupt font file.** In a copy of the package (made with
  `support.copy_package`, run from that copy):
  - without `YujiBoku-Regular.ttf`, or with
    `NotoSerifJP-SemiBold.otf` truncated to half, a C-4 run exits 1 with a
    message naming the file's path, and writes no file;
  - under `--json` the same is one `error` event and no `done`;
  - no system font is used instead;
  - the fonts are validated up front, including every table's offset and
    length against the file size: a truncated OTF can still have a
    parseable cmap (Agreement 7).

### The PDF

- **AC-11 Page and validity.** For C-1, C-3, C-4, C-4b and C-5:
  - one page, MediaBox `[0 0 1190.55 841.89]` (±0.01 pt) on the `/Page`
    object itself (not inherited), no `/Rotate` other than 0;
  - every stream is `/FlateDecode` or unfiltered (images may use Flate only);
  - `%PDF-1.x` header, ending in `%%EOF`;
  - `startxref` points at the cross-reference table or stream, and every
    in-use entry points at its object (`refkit.xref_problems` is empty);
  - pdfium opens and renders it.
  - Manual M-4: `qpdf --check` (pikepdf `check_pdf_syntax()`) reports no
    problem.
- **AC-12 Outlines, no fonts.** No PDF has a `/Font`, `/FontDescriptor` or
  `/FontFile*` object, nor a `Tf`/`Tj`/`TJ` operator. Glyphs are filled
  paths, written inline in the page content (no Form XObject reused per
  glyph): the flat and proof PDFs have more than 1000 path operators each
  (prototype: C-4 8075, C-5 5757). The text is not searchable, as the user
  accepted.
- **AC-13 Vector stays vector.**
  - The flat and proof PDFs hold no image.
  - An inked overlay holds exactly one image: `/DeviceGray`, with a soft
    mask that is itself `/DeviceGray`.
  - The crest and the ring are paths in every variant.
- **AC-14 Grey overlays, coloured guides.**
  - In `overlay` and `overlay-flat` (C-1, C-3, C-4, C-4b), every colour
    operator is `g` or `G`. Any `cs`/`CS` names `/DeviceGray`. No
    transparency group names a colour space other than `/DeviceGray`. The
    image and its soft mask are `/DeviceGray`.
  - Rasterised in colour by pdfium, these pages have R = G = B at every
    pixel.
  - The proof (C-5) keeps its guide colours: `#d8c9a8`, `#cddbe8` and
    `#e4b9b9` strokes are present (`RG`). Its PNG shows the stock-border
    line in that colour (each channel within 24 of 216, 201, 168).
  - Manual M-5: `gs -sDEVICE=inkcov` on C-1 and C-4 gives C = M = Y =
    0.00000.
- **AC-15 Deterministic.** The same command twice (C-1 and C-4, `-f pdf,png`,
  same machine) gives byte-identical PDFs and PNGs, with no normalising.
  Reported in M-3: the macOS arm64 and Linux x86_64 PDFs are byte-identical,
  and the PNGs differ by at most 1 per channel.
- **AC-16 Other viewers (manual M-4).** C-1, C-3, C-4 and C-5 rasterised by
  Ghostscript, poppler (`pdftoppm`) and macOS Preview (`sips` or Quartz) at
  150 dpi, against the package's own PNG composited on white and
  box-filtered to 150 dpi:
  - SSIM ≥ 0.95;
  - mean ink coverage over the text columns within ±0.02, which shows the
    soft mask is honoured.

### The PNG

- **AC-17 Size, resolution, background, ink.**
  - Pixel size equals today's: 4961 × 3508 at the default 300 dpi, and
    2480 × 1754 for C-8.
  - The pHYs chunk gives the requested dpi within 0.05. pHYs counts whole
    pixels per metre: 150 dpi is 5905.5, which Inkscape writes as 5905
    (149.987) and Pillow as 5906 (150.012).
  - Every variant's PNG is transparent where nothing is drawn (corner alpha
    0), as today, the proof included.
  - Mode is RGBA, or LA (grey with alpha) for `overlay` and `overlay-flat`
    (Q-3). The proof is RGBA.
  - Solid ink (alpha 255 after a 2 px erosion) has the colour `#111111`,
    within 2 per channel.
  - Nothing coloured: in `overlay` and `overlay-flat`, no pixel with
    alpha > 32 has a chroma over 12.

### Looks like today

Method: `refkit` on both sides. Rasters are greyscale composited on white.
The candidate is moved onto the reference by sub-pixel cross-correlation
when the offset exceeds 0.1 px, and the offset is reported. Regions use a
3 × 3 opening on the |Δ| > 64 mask.

- **AC-18 Whole page.**
  - The PDF at 150 dpi against `<case>-pdf150.png`: SSIM ≥ 0.98 for C-4,
    C-4b and C-5, and ≥ 0.97 for C-1 and C-3. Mean |Δ| ≤ 2.0/255. The global
    offset is ≤ 0.5 px (0.085 mm).
  - The PNG as written, composited and halved alike, against `<case>-png.png`
    for every case including C-8: SSIM ≥ 0.97 and mean |Δ| ≤ 2.0/255.
  - Spike, for scale: 0.9997 and 0.07.
- **AC-19 Columns and crest, 600 dpi.** For every text column and the crest
  of every PDF case:
  - SSIM ≥ 0.95;
  - no connected difference region over 0.3 mm²;
  - ink (Σ (255 − grey)) within ±3 % of the reference crop.
- **AC-20 Glyph placement.**
  - For the flat cases (C-4, C-4b, C-5), every glyph's cell is within
    0.15 mm of the reference, by sub-pixel cross-correlation after global
    alignment.
  - For every case with a PDF, each crest-ring glyph's ink centroid, inside
    the band between the rings, is within 0.15 mm.
  - Report the worst of each.
- **AC-21 The text layer.** C-1 and C-3 with `-f svg,pdf`: the shipped
  `-textlayer.png` and the `<image>` element in the inked SVG, against
  today's:
  - pixel size within 1 px per side;
  - x, y, width and height within 0.05 mm;
  - IoU of graded alpha > 128 ≥ 0.98;
  - total graded alpha within ±2 %;
  - every pixel with alpha > 0 has RGB `(17, 17, 17)`;
  - the layer's pixel size is `round(mm × 600 / 25.4)` of its box, ±1.
- **AC-22 Looks good (manual M-2).** The tester renders the side-by-side
  and crop sheets the spike made into
  `docs/work/render-without-inkscape/compare/`: today left, new right,
  |Δ| × 4. They cover C-1, C-3, C-4, C-4b, C-5 and C-8, and one traced
  crest glyph. Checked at 600 dpi:
  - no missing, substituted or wrongly rotated glyph;
  - small kana ァ ェ ョ upper right, ー vertical, ・ centred, the shrunk
    name the same size, the date in kanji;
  - no halo or ragged edge on the inked text, no jagged edges, no raster
    where today has vector.

  The user looks at them before the commit (or after it, with the print
  tests).

### Compatibility

- **AC-23 CLI and `--json` unchanged.**
  - `--help` offers exactly today's options: `--all --awards --clean
    --config --date --dpi --example-config --formats --help --honorific
    --json --list --name --no-ink --out --rank --suffix --variants
    --version`, with short forms `-a -c -d -f -h -n -o -r -v`.
  - The stage keys, labels, step counts and totals are unchanged (the
    existing `test_ac_json.py` and `test_ac_plain_white.py` tables).
  - Each `pdf` and `png` progress event is reported before its file exists
    (spike, K-1: announce `pdf` before building the PDF).
  - Every failure still ends in exactly one `error` event, with exit 1.
- **AC-24 The writer refuses what it does not handle.** If `document()`'s
  SVG carries an element, attribute or path command the writer does not
  implement (tested: an `<ellipse>`, a `<use>`, a `style="…"` attribute,
  injected into an overlay-flat run), the run fails:
  - exit 1, with a message naming the element or attribute, and under
    `--json` one `error` event;
  - no PDF is written, and no `.work` is left. `.work` is cleaned up on
    every failure, not only this one (Agreement 8).

  It never silently drops what it does not handle (spike, risk 1).
- **AC-25 SVG output and the regression goldens.** `-f svg` writes what it
  wrote, `<text>` elements included. The regression suite changes in
  exactly these ways:
  - `golden_lib.run_case` runs the generator with no stand-in program on
    `PATH` (`/usr/bin:/bin` only). Every case now renders for real, the
    inked ones included.
  - `test_golden.py` no longer compares `tools`, the Inkscape calls, which
    no longer exist. The manifest keeps them, unchanged, as history.
  - The inked SVGs are compared byte for byte, except for the four numbers
    in the text layer's `<image x=… y=… width=… height=…>`. These came from
    the stand-in's fixed query answer and are now the real box (AC-21
    checks them). The element's form stays: `xlink:href`,
    `preserveAspectRatio="none"`, 4 decimals.
  - The text-layer SVGs (the `document(…, layer="text")` output that today
    goes to Inkscape) are captured by `golden_driver.py` wrapping
    `build_diploma.document`. They are compared as a sorted list of sha256 values (each layer drawn as often as in the baseline),
    since their file names were the stand-in's. So the text layer must still
    be drawn from `document(…, layer="text")`, looked up as the module
    attribute `build_diploma.document`.
  - `test_output_matches_baseline` carries the `render` marker.
  - Everything else stays byte for byte: every other SVG, stdout, the files
    written, `--list`. The manifest itself does not change; its source
    stays `823af58`.
  - `make_golden.py` keeps `--current`. A `--ref` older than this item would
    need a real Inkscape, so the README says so.

### Memory and time (`measure.sh`, `menkyo-test` image, native arm64 Docker on the Mac, median of 3)

Today (8509b85 in `Dockerfile.ref`, 2026-10-29, median of 3):

| case | what | peak `memory.peak` | wall |
|---|---|---|---|
| C-1 | overlay, pdf + png | 413 MB | 3.63 s |
| C-1p | overlay, pdf (the portal's run) | 413 MB | 3.06 s |
| C-4 | overlay-flat, pdf + png | 103 MB | 0.76 s |
| C-4p | overlay-flat, pdf | 103 MB | 0.36 s |
| C-5 | proof, pdf + png | 102 MB | 0.76 s |

The original figure the user refers to is 933 MB (C-1 before ink-memory).
For scale, `python -c "import numpy, PIL.Image, pypdfium2, fontTools.ttLib"`
peaks at 33–53 MB in a pip-only container, and about 83 MB with
`scipy.ndimage`.

- **AC-26 Peak memory.**
  - C-1 and C-1p: **≤ 320 MB**. That is about a third of 933 MB (34 %) and
    77 % of today's 413 MB (Q-2).
  - C-4 and C-4p: **≤ 110 MB**, the spike's Inkscape figure. Between 110 and
    150 MB it passes only if DECISIONS.md justifies it with the measured
    floor (the same container importing exactly what a flat run imports) and
    the render's share above that floor.
  - C-5 (proof, colour): ≤ 150 MB.
  - Above 150 MB for any flat case, or above 320 MB for C-1, is a FAIL.
  - Figures go in DECISIONS.md and validation.md, with today's beside them.
  - Automated guard (render tests, any machine): the `menkyo` process's own
    peak RSS is ≤ 400 MB for C-1 and ≤ 160 MB for C-4.
- **AC-27 Time.** C-1's median wall time is ≤ today's; C-4's and C-5's
  are ≤ 1.1 × today's (noise is about ±5 % at 0.76 s) (Agreement 9). All
  measured on the same machine on the same day with `measure.sh` and
  `Dockerfile.ref` (spike: 0.81 and 0.74). Also report the stage split. The
  automated guard: a C-1 run finishes within 60 s.

### Wheel and platforms

- **AC-28 Wheel.**
  - `menkyo/fonts/` holds both fonts, `OFL.txt` and the new licence. The
    font bytes equal the checkout's.
  - The payload is exactly `src/menkyo` (no tests, no fixtures).
  - `Requires-Dist` is as AC-2.
  - The wheel is ≤ 11.5 MB (today 5.14 MB, spike 10.53 MB).
- **AC-29 Installed outside the checkout.**
  - Automated (slow, render): the wheel in a throwaway venv, run from a
    temporary directory with `PATH` = the venv's `bin` plus `/usr/bin:/bin`,
    renders C-1 and C-4 (`--example-config` written to a file, then
    `-c` it). The PDFs pass AC-11, AC-12 and AC-14's operator check, and the
    `done` event lists them. This runs on the Mac with `uv run pytest`, and
    in the Linux image with `scripts/test-docker.sh`.
  - Manual M-3 (Linux x86_64): in `python:3.13-slim-bookworm` with
    `--platform linux/amd64`, `pip install` of the wheel and nothing else
    (no `apt-get`), `dpkg -l | grep -Ei
    'inkscape|fontconfig|fonts-noto|poppler|ghostscript|cairo'` is empty.
    `menkyo` renders C-1 and C-4 from `/tmp`, and the files pass the same
    checks.
- **AC-30 Python 3.11–3.13 (manual M-6).** `uv pip compile --only-binary
  :all:` of the runtime dependencies resolves for 3.11, 3.12 and 3.13 on
  `aarch64-apple-darwin` and `x86_64-manylinux_2_28`. `uv sync --frozen`
  works on the Mac.

### Test infrastructure

- **AC-31 `render` marker, no fakes.**
  - The `render` marker stays, meaning "does a real render (seconds)", so
    `-m "not render"` is the quick run. Render tests never skip: nothing
    can be missing.
  - `REQUIRE_RENDER` is gone from `tests/conftest.py`,
    `tests/docker/Dockerfile`, `scripts/test-docker.sh`, the workflow,
    `pyproject.toml` and `tests/README.md`.
  - The `inkscape`, `fake_tools` and `no_tools` fixtures, `require_program`,
    `support.make_fake_bin`, `support.find_inkscape` and `tests/fakes/` are
    gone.
  - `uv run pytest -rs` on the Mac reports no skipped `render` test (M-1).
- **AC-32 Slim test image.**
  - `tests/docker/Dockerfile` is `FROM python:3.13-slim-bookworm` with no
    `apt-get` at all. It keeps the personal-data guard.
  - `scripts/test-docker.sh` builds it and runs the whole suite, which
    passes (M-1).
  - The image's size is reported against today's 1.44 GB.
- **AC-33 Workflow.** `.github/workflows/package.yml` has no `apt-get` step,
  no `pdffonts` and no `REQUIRE_RENDER`. It still runs `uv run --frozen
  pytest`, and its smoke test still installs the built wheel outside the
  checkout, renders `-v overlay,overlay-flat` with `--json` and checks the
  `done` event.

### Docs

- **AC-34 README.**
  - No `Inkscape`, `fontconfig`, `apt-get`, `poppler` or `fonts-noto` left.
  - Quick start and "As a package" say there is nothing to install beside
    the wheel's own dependencies.
  - The `error` event example no longer reads `"inkscape failed."`, and a
    missing-glyph error is described (an `error` event naming the
    character).
  - "How it looks the way it does" no longer says fontconfig. It names both
    fonts, Yuji Boku and Noto Serif JP SemiBold.
  - The layout block's `fonts/` line names both.
  - The PDF's text being outlines (not searchable) is stated once.
- **AC-35 DECISIONS.md.**
  - A new dated entry whose heading names Inkscape (e.g. "Rendered without
    Inkscape"), dated with either dash (`## 2026-10-29 – …`, house style, or
    `—`). It records the family-name mapping (AC-1). It covers the route (fontTools, our own writer, pdfium);
    the crest font and its size; outlines, not searchable; DeviceGray
    overlays; the missing-glyph error; greyscale for the flat variants; and
    AC-26's and AC-27's figures, before and after, with the wheel size.
  - It names the older entries it overrides, as "Plain white paper only"
    did, rather than editing them: "The font is vendored, not installed",
    the text-layer bullet of "Output, and the supersampling cap", "Cost:
    the text becomes a raster" where it says Inkscape, "Installed-copy
    behaviour is kept" (tools on PATH), and "Packaging is tested by
    rendering" (pdffonts).
  - Every entry up to and including "Supersampling removed" is
    byte-for-byte as at 8509b85.
  - The Open item "Render without Inkscape" is gone; the others stay.
  - `## Open` gains an item for the house-style sweep of the existing docs
    (the user decided 2026-10-29); its text mentions the house style.
- **AC-36 NOTICE, tests/README, pyproject.**
  - NOTICE as AC-3.
  - `tests/README.md` describes the slim image, the `render` marker without
    `REQUIRE_RENDER`, no stand-in program, the reference fixtures, the
    golden changes of AC-25, and that `make_golden.py --ref` needs a
    commit from this item on.
  - In `pyproject.toml`, the `render` marker's text does not mention
    Inkscape.
- **AC-37 Version (Q-1).** `pyproject.toml`, `menkyo --version` and the wheel
  name carry the version the user chooses. Tester's recommendation:
  `0.3.0`.

### Nothing else changes

- **AC-38 The rest of the suite.** The whole suite passes, migrated as listed
  below (`uv run pytest` on the Mac, `scripts/test-docker.sh`). Its
  remaining contracts hold unchanged: config, paths, the `--json` events,
  `--list`, plain stdout, file names, `.work` removed after a run, and
  `--clean`. The ink-memory render tests wrap `menkyo.ink.ink_layer`, so the
  text layer still reaches the ink pass as one call per inked document,
  `ink.ink_layer(png_path, out_path, 600.0)`, looked up as a module
  attribute, with the 600 dpi text layer saved as a PNG first. That pre-ink
  PNG carries alpha (LA or RGBA) and colour 17 (`#111111`) (Agreement 2).
  The graded alpha is bit for bit what today's `ink_layer` makes from it
  (ink-memory's tests stay green), whatever `ink.py` changes outside the
  grading (Agreement 1).

## Test approach

New automated tests:
`tests/acceptance/test_ac_render_without_inkscape.py`, with the fixtures
and kit in `tests/acceptance/render_without_inkscape/`. Renders that several
tests share run once per module in a session-scoped `HOME`. Tests marked
`render` do a real render; `slow` builds and installs the wheel.

| AC | automated | manual |
|---|---|---|
| AC-1 | `test_ac1_renders_with_an_empty_path`, `test_ac1_no_inkscape_fontconfig_or_subprocess_in_the_package`, `test_ac1_no_system_font_lookup` | — |
| AC-2 | `test_ac2_dependencies`, `test_ac2_pyproject_names_no_system_programs` | `uv lock --check` (M-6) |
| AC-3 | `test_ac3_yuji_boku_unchanged`, `test_ac3_crest_font_is_noto_serif_jp_semibold`, `test_ac3_crest_font_licence`, `test_ac3_notice` | — |
| AC-4 | `test_ac4_inkscape_helpers_removed`, `test_ac4_no_fontconfig_dir_left` | — |
| AC-5 | `test_ac5_missing_glyph_in_a_flag[…]` | — |
| AC-8b | `test_ac5_sample_name_is_named_by_its_key`, `test_ac5_sample_rank_only_where_a_grade_is_drawn`, `test_ac5_honorific_only_with_a_name`, `test_ac5_only_the_selected_awards_are_checked` | the writer's cmap backstop: review |
| AC-6 | `test_ac6_missing_glyph_json[…]` | — |
| AC-7 | `test_ac7_missing_glyph_in_config[…]` | — |
| AC-8 | `test_ac8_nothing_written_for_any_award`, `test_ac8_clean_keeps_the_directory_on_error` | — |
| AC-9 | `test_ac9_list_is_not_checked`, `test_ac9_space_slash_colon_render`, `test_ac9_traced_glyph_stands_in_for_the_font`, `test_ac9_traced_glyph_with_an_arc_is_refused` | — |
| AC-10 | `test_ac10_missing_body_font`, `test_ac10_truncated_crest_font`, `test_ac10_font_error_json` | — |
| AC-11 | `test_ac11_page_and_validity[…]` | M-4 |
| AC-12 | `test_ac12_outlines_no_fonts[…]` | — |
| AC-13 | `test_ac13_images[…]` | — |
| AC-14 | `test_ac14_overlays_are_grey[…]`, `test_ac14_overlay_raster_has_no_colour[…]`, `test_ac14_proof_keeps_its_guide_colours` | M-5 |
| AC-15 | `test_ac15_deterministic[C-1,C-4]` | M-3 |
| AC-16 | — | M-4 |
| AC-17 | `test_ac17_png[…]` | — |
| AC-18 | `test_ac18_page_pdf[…]`, `test_ac18_page_png[…]` | — |
| AC-19 | `test_ac19_columns_and_crest[…]` | — |
| AC-20 | `test_ac20_glyph_placement[C-4,C-4b,C-5]`, `test_ac20_crest_ring[…]` | — |
| AC-21 | `test_ac21_text_layer[C-1,C-3]` | — |
| AC-22 | — | M-2 |
| AC-23 | `test_ac23_help_offers_todays_options`, `test_ac23_progress_before_the_file`; the stage tables in `test_ac_json.py`, `test_ac_plain_white.py` | — |
| AC-24 | `test_ac24_unsupported_svg_is_refused[ellipse,use,style]` | — |
| AC-25 | `tests/regression/test_golden.py` (migrated) | review the diff of `tests/regression/` |
| AC-26 | `test_ac26_process_peak_guard[C-1,C-4]` | M-1 (`measure.sh`) |
| AC-27 | `test_ac27_time_guard` | M-1 |
| AC-28 | `test_ac28_wheel_fonts_and_size`, `test_ac_wheel.py` | — |
| AC-29 | `test_ac29_installed_wheel_renders` | M-3 |
| AC-30 | — | M-6 |
| AC-31 | `test_ac31_no_require_render_and_no_fakes` | M-1: `-rs` shows no skip |
| AC-32 | `test_ac32_test_image_is_slim` | M-1 |
| AC-33 | `test_ac33_workflow` | — |
| AC-34 | `test_ac34_readme` | read it |
| AC-35 | `test_ac35_decisions_entry`, `test_ac35_history_untouched`, `test_ac35_open_item_closed` | read it |
| AC-36 | `test_ac36_tests_readme_and_marker` | read it |
| AC-37 | `test_ac37_version` (expects `0.3.0` until the user decides) | — |
| AC-38 | the whole suite | — |

### Manual checks (VALIDATE)

- **M-1 Suites, memory and time.**
  - `uv run pytest -rs`: all pass, no `render` skip.
  - `scripts/test-docker.sh`: all pass; note the image size (`docker image
    inspect menkyo-test`, plus `du -sx /` in it).
  - Then measure with a snapshot of the working tree's `src/`:

    ```sh
    T=$(mktemp -d); cp -R src "$T/"
    tests/acceptance/render_without_inkscape/measure.sh menkyo-test "$T" /opt/venv/bin/python 3
    ```

  - For today's figures on the same day:

    ```sh
    B=$(mktemp -d); git archive 8509b85 src/menkyo | tar -x -C "$B"
    docker build -q -f tests/acceptance/render_without_inkscape/Dockerfile.ref \
      -t menkyo-inkscape-ref tests/acceptance/render_without_inkscape
    tests/acceptance/render_without_inkscape/measure.sh menkyo-inkscape-ref "$B" python 3
    ```

  - Compare against AC-26 and AC-27.
- **M-2 Comparison images.** Render the cases with the new code. Write
  side-by-side sheets (100 dpi) and 600 dpi crop sheets (today | new |
  |Δ| × 4) from `reference/` and the new output into
  `docs/work/render-without-inkscape/compare/`, ≤ 15 MB in total, and look
  at every one (AC-22). Use placeholder data only.
- **M-3 Linux x86_64.** Build the wheel. Then:

  ```sh
  docker run --rm --platform linux/amd64 -v "$PWD/dist":/d:ro \
    python:3.13-slim-bookworm sh -c '
      pip install -q /d/menkyo-*.whl && cd /tmp
      dpkg -l | grep -Ei "inkscape|fontconfig|fonts-noto|poppler|ghostscript|cairo"
      menkyo --example-config > ex.toml
      menkyo -c ex.toml -a dan -v overlay -n ヤン・ヤンセン -r 2 -d 2024-07-01 -f pdf,png --out o --json
      menkyo -c ex.toml -a dan -v overlay-flat -n アレクサンドル・ファン・デル・フェルデン -r 10 -d 2020-10-20 -f pdf,png --out o --json'
  ```

  The `grep` prints nothing. Copy the outputs out and run the AC-11, AC-12
  and AC-14 checks on them, plus AC-15's cross-platform comparison with the
  Mac's. For that byte comparison, install the same dependency versions as
  the Mac: `uv export --no-dev --no-hashes > c.txt` and
  `pip install -c c.txt /d/menkyo-*.whl` (Agreement 10).
- **M-4 Viewers.** Run `pikepdf.Pdf.open(p).check_pdf_syntax()` in a
  throwaway venv. In a throwaway container with `ghostscript
  poppler-utils`, rasterise C-1, C-3, C-4 and C-5 at 150 dpi. On the Mac use
  `sips` or Quartz. Score as AC-16.
- **M-5 inkcov.** `gs -q -o - -sDEVICE=inkcov` on C-1 and C-4, in the same
  throwaway container.
- **M-6 Resolution.** `uv lock --check`, then
  `uv pip compile --only-binary :all: --python-version 3.1{1,2,3}
  --python-platform {aarch64-apple-darwin,x86_64-manylinux_2_28}` on the
  runtime dependencies. All six resolve.

## Changes to the existing suite (tester, before the developer starts)

Only the tester changes `tests/acceptance/` and `tests/regression/`. These
tests encode Inkscape, the stand-in or the old dependency set. The user's
decision for this item supersedes them, and they are migrated as follows,
together with the new tests, so the developer has the whole target:

| file | change |
|---|---|
| `tests/conftest.py` | drop `REQUIRE_RENDER`, `FakeTools`, `fake_tools`, `no_tools`, `inkscape`, `require_program` |
| `tests/support.py` | drop `make_fake_bin`, `FAKE_TOOL`, `find_inkscape` |
| `tests/fakes/` | deleted |
| `acceptance/test_ac_json.py` | real renders with `support.isolated_env`. `test_ac9_inkscape_missing` and `test_ac9_inkscape_fails`, and the stand-in half of `…_from_the_real_command`, are superseded by AC-10 and AC-24 |
| `acceptance/test_ac_cli.py` | real renders. `test_ac11_plain_missing_inkscape` is superseded by AC-1 |
| `acceptance/test_ac_paths.py` | `test_ac4_installed_copy_writes_to_documents`: real render, no fontconfig assertion (AC-10 shows the copy's own fonts are read) |
| `acceptance/test_ac_render.py` | pdfinfo/pdftoppm/pdffonts replaced by `refkit`/pypdfium2. "embeds Yuji Boku" becomes "outlines, no font" (AC-12) |
| `acceptance/test_ac_wheel.py` | real renders. The fontconfig assertions go; the `pdffonts` check becomes AC-12's |
| `acceptance/test_ac_plain_white.py` | real renders. `ac5` "needs only inkscape" becomes "needs no program". `ac5_ghostscript_is_not_a_known_tool` goes, since there is no tool list. `ac15` no longer requires Inkscape in Quick start. `ac16` expects "Render without Inkscape" retired. `ac17` drops the CLAUDE.md, pyproject-comment and marker assertions about Inkscape. `ac18` becomes "no apt-get at all". `ac23` (0.2.0) is superseded by AC-37 |
| `acceptance/test_ac_remove_supersample.py` | real renders. `ac6`'s Inkscape `--export-dpi=600` check becomes the 600 dpi pixel-size check (AC-21) |
| `acceptance/test_ac_cli_only.py` | `ac3_paths_api_kept` keeps only the four path functions that stay. `ac5_runtime_dependencies_unchanged` becomes AC-2's five. `ac5_dev_group_is_pytest_only` is unchanged |
| `acceptance/test_ac_ink_memory.py` | `ac13_no_new_dependencies` is superseded by AC-2. The render tests drop the `inkscape` fixture |
| `acceptance/test_ac_release.py` | `ac14` no longer requires `REQUIRE_RENDER`; `ac15` no longer requires it in the Dockerfile |
| `test_packaging_fixes.py` | real renders |
| `regression/golden_lib.py`, `golden_driver.py`, `test_golden.py`, `make_golden.py`, `golden_cases.py` | as AC-25 |

Applied in PLAN mode, 2026-10-29. Two checks show that the migration and
the new kit are sound before any production code exists:

- **The migrated suite, against today's code with real Inkscape.** The
  regression suite and every migrated file except the new one ran in the
  existing `menkyo-test` image, with the working tree's `tests/` and `src/`
  mounted: 355 passed, 10 failed. All 10 failures are new-contract
  assertions: no pypdfium2 yet (`test_ac_render.py` ×4), Inkscape and apt
  still present (`plain_white` ac5 ×2, ac15, ac18 ×2), and one scan hit in
  the new test file, since fixed. The golden comparison of AC-25 (text-layer
  hashes, `<image>` box normalised) passes on today's output.
- **The new tests, against the spike's prototype renderer.** The prototype
  (`docs/work/no-inkscape/proto/render_candidate.py`, run on 8509b85's
  `src/` in `menkyo-spike-cand`) was scored by the new tests' own functions:
  54 of 56 checks pass. PDF 150 dpi SSIM 0.9996–0.9997, MAD ≤ 0.075.
  Column crops ≥ 0.9948 (C-4 name; ink +0.87 %). Worst glyph 0.049 mm (C-4
  フ). Ring 0.024 mm. Text layer IoU 0.9945 / 0.9944. The two failures are
  real findings for the build:
  - the prototype writes the proof PNG opaque, where today's is
    transparent (AC-17; the spike's risk 4);
  - the pHYs tolerance was too tight at 150 dpi. It was corrected to 0.05
    (AC-17).

## Test changes (tests/acceptance, tests/regression)

After IMPLEMENT, 2026-10-29. Both changes are decided by the tester; the
contract did not change:

- **`test_ac35_decisions_entry`.** It asked for exactly one dated heading
  naming Inkscape. But the existing 2026-10-28 entry "`xlink:href` for the
  inked text, for Inkscape 1.2" names it too, and AC-35 forbids touching it.
  The test now counts only entries dated 2026-10-29 or later whose heading
  was not already in DECISIONS.md at 8509b85 (without git, as in the Docker
  image, the date filter alone). This was a test bug.
- **`test_ac_remove_supersample.py::test_ac5_no_supersample_parameter`.** It
  pinned `_inked_text_image(base, verb, heading, kw, env)`. `env` was the
  Inkscape tool environment, so it is meaningless now. The test now pins
  `base, verb, heading, kw` and forbids any supersampling parameter, so the
  developer may drop `env`. Recorded in remove-supersample's acceptance.md
  too.
- **`tests/regression/test_golden.py`, text layers (review R-7).** The
  comparison deduplicated only the current side (`sorted(set(got))` against
  `sorted(golden)`). A baseline with two identical layers would have failed,
  and a run that drew one layer twice would have passed. Both sides are now
  sorted lists, so every text layer must be drawn exactly as often as the
  baseline drew it. AC-25's "compared as a set" now reads "as a sorted list
  of sha256 values". `tests/regression`: 124 passed.
- **Q-7, flat and proof PDF hashes (VALIDATE round 1).** The user approved
  pinning them. They live in a new `tests/regression/golden/pdf_sha256.json`
  (a `note` on fontTools bumps, the fontTools version, and per case the
  sha256 of every `-overlay-flat` and `-proof` PDF), not in
  `manifest.json`, so AC-25's "the manifest itself does not change; its
  source stays `823af58`" still holds. `make_golden.py --pdf-hashes`
  rewrites that file only, from the working tree. `test_output_matches_baseline`
  now also asserts that the flat/proof PDFs a case writes are exactly the
  pinned ones, byte for byte (cases `inked`: 6 PDFs, `flat-pdf`: 2), and
  `test_pdf_hashes_cover_known_cases` guards the file. Inked overlay PDFs
  and PNGs carry pdfium's raster and stay unpinned.
- **Q-7 follow-up (review round 2, R-11).** Q-7's text named
  `make_golden.py --current`; the flag is `--pdf-hashes`, now corrected
  there. `test_golden.py` read `pdf_sha256.json` at import, so a missing
  file broke collection of the whole suite. It is now read inside the two
  tests that use it (`_pdf_hashes()`); a missing file fails those tests
  with a message pointing at `make_golden.py --pdf-hashes`. The user
  decided that `--dpi` 1–2400 is checked on every run, `--list` included
  (validation F-2), so no test changes for it.



- **Q-1 Version.** The dependency set changes (two new wheels, no system
  programs), and the portal's image can drop four apt packages.
  Recommendation: **0.3.0**. `test_ac37_version` expects 0.3.0 until the
  user says otherwise.
- **Q-2 What "roughly a third" means for C-1.** Recommendation: **≤ 320 MB**
  cgroup `memory.peak`, median of 3, `menkyo-test` image, native arm64
  Docker on the Mac. That is 34 % of 933 MB and 77 % of today's 413 MB.
  The ink pass alone is about 263 MB above a fresh process (ink-memory), so
  320 MB leaves pdfium and the page raster little room. If it is missed by
  a few MB, should the figure stand as measured (the user decides), or is
  it a FAIL?
- **Q-3 PNG mode of the flat and overlay PNGs.** Greyscale rendering is
  cheapest if the PNG becomes LA (grey + alpha) instead of RGBA. It looks
  identical and every viewer and browser reads it. Does the portal care?
  Recommendation: **allow LA** for `overlay` and `overlay-flat`. The proof
  stays RGBA, since its guides are coloured.
- **Q-4 Proof memory.** The proof cannot be greyscale (coloured guides), so
  the flat target does not apply to it. Recommendation: **≤ 150 MB**, as in
  AC-26 (today 102 MB with Inkscape). It is a check sheet, not the portal's
  run.
- **Q-5 CLAUDE.md.** Resolved: the orchestrator updates the "Inkscape
  renders" line at commit time. Not in the developer's scope.
- **Q-6 Naming the source of a missing character.** AC-5 and AC-7 require
  the message to name the flag or configuration key, beyond "names the
  character". The portal can then point at the field. This is the tester's
  addition; recommendation: keep it.
- **Q-7 Byte goldens for the new route.** The flat and proof PDFs depend
  only on our writer and fontTools, not on pdfium, so their sha256 could be
  pinned in the regression manifest once validated. A future item would
  then see any change it makes to them. PNGs and inked PDFs depend on
  pdfium, so they are not pinned. Recommendation: **yes, for flat/proof PDFs
  only**, added by the tester in VALIDATE (a `pdf_sha256` per case,
  regenerated with `make_golden.py --pdf-hashes`; see Test changes).
- **Q-8 `--list` with a missing character.** Recommendation: **unchanged**
  (AC-9). It renders nothing and today it never fails on content. The
  portal gets the error from the real run, before anything is written.

## Agreement

Round 2, 2026-10-29. The developer: ready to build. Its clarifications,
relayed by the orchestrator and folded into the criteria above:

1. **ink.py** may change outside the grading (`coverage()` reads LA without
   the RGBA round trip, scipy imported lazily). The graded alpha is bit for
   bit unchanged and the ink-memory tests stay green. → Scope, AC-38.
2. **The pre-ink PNG** carries alpha (LA or RGBA) with colour 17. → AC-38.
3. **refkit's implicit constraints** are now explicit: `/MediaBox` on each
   `/Page`; streams Flate or unfiltered; glyph outlines inline, with no Form
   XObject reuse; more than 1000 path operators for flat and proof (the test
   now asks that of C-5 too; prototype 5757). → AC-11, AC-12.
4. **Font families:** `font-family="Noto Serif CJK JP SemiBold"` stays byte
   for byte in the SVG. The writer maps it to the vendored Noto Serif JP
   file, and DECISIONS records the mapping. → AC-1, AC-35 (the test looks
   for "Noto Serif CJK JP" in the entry).
5. **Glyph-check scope:** exactly what is drawn, with the message naming
   `[sample] …` and config sources, and the writer's cmap backstop. → the
   preamble to AC-5, new AC-8b, four new tests. The backstop is checked by
   review, since it is unreachable from the CLI once the up-front check
   works.
6. **A traced glyph with an arc** is refused, naming the crest file. → AC-9,
   one new test.
7. **Fonts validated up front,** table extents included. → AC-10.
8. **`.work`** is cleaned up on any failure. → AC-24.
9. **Time:** C-4 and C-5 ≤ 1.1 × today's; C-1 no slower. → AC-27.
10. **M-3** pins the Mac's dependency versions for the byte comparison. → M-3.
11. **Nits:** `support.read_log` was unused and is removed. `conftest`'s
    unused `Path` import is removed; `shutil` is used (`rmtree`, `which`)
    and stays.

Also from the orchestrator:

- **House style.** The `docs` agent writes README, DECISIONS,
  `tests/README.md` and NOTICE in the user's house style. The AC-34 to
  AC-36 tests accept either dash in a dated heading, and check substance:
  named entries, figures (`N MB` with or without a space), the Open items,
  the "outline" and "not searchable/copyable" facts. They no longer check
  exact phrasing ("bundled fonts" became "fonts" in the Licence section).
  `## Open` gains a house-style sweep item (the user's decision,
  2026-10-29). → AC-35, `test_ac35_open_item_closed`.
- **Q-5:** the orchestrator updates CLAUDE.md, outside the developer's scope.

Recommendations the developer agrees with, still awaiting the user (the
orchestrator asks): Q-1 0.3.0; Q-3 LA allowed; Q-4 proof ≤ 150 MB; Q-6 name
the source; Q-7 flat/proof PDF hashes in the goldens, with a manifest note
that a fontTools bump may change them; Q-8 `--list` unchanged.

**Q-2, the orchestrator's proposal to the user:** C-1 target ≤ 320 MB;
320–350 MB passes only if DECISIONS justifies it with the measured floor
(the ink pass alone); above 350 MB is a FAIL. AC-26 stays at ≤ 320 MB until
the user answers; the automated guard (400 MB process RSS) is unaffected.

**Disagreements:** none.

## User approval (2026-10-29)

The user approved the plan. Answers:
- Q-1: version 0.3.0.
- Q-2: C-1 target ≤ 320 MB; 320–350 MB passes only if DECISIONS justifies it with the measured floor (the ink pass alone); above 350 MB fails.
- Q-3: LA PNGs allowed for overlay and overlay-flat.
- Q-4: proof ≤ 150 MB.
- Q-6: the missing-character message names its source flag or config key.
- Q-7: flat and proof PDF hashes are pinned in the goldens, with a manifest note on fontTools bumps.
- Q-8: `--list` is unchanged.
- Q-5: the orchestrator updates CLAUDE.md at commit time.
- Existing docs are restyled in a separate later item. This item adds it to `## Open` and styles new and changed text only.
