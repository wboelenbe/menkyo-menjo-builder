# Spike: a menkyo without Inkscape (no-inkscape)

Contract: [acceptance.md](acceptance.md), revision 2. Baseline HEAD `90e5799`.
Everything here was measured on 2026-10-28 on the user's Mac (macOS, arm64,
OrbStack Docker 29.8.2: native `linux/arm64`, `linux/amd64` under emulation).
Every number comes from a command in [proto/](proto/); the one script that
reruns them all is [proto/reproduce.sh](proto/reproduce.sh) (its header lists
the steps), and the raw outputs it writes are the files named in brackets,
e.g. `[run/metrics.json]` means `WORKDIR/run/metrics.json`. Estimates are
marked *estimate*.

## Recommendation

**Render without Inkscape: keep `document()`, turn every `<text>` into glyph
outlines with fontTools, write the PDF with a small writer of our own (about
215 lines of code, the outline step another 60), and rasterise that PDF with
pdfium (pypdfium2) for the PNG and for the 600 dpi text layer.** It passes every hard criterion. On screen it is
indistinguishable from Inkscape (whole-page SSIM ≥ 0.9997, mean difference
≤ 0.08/255, no glyph more than 0.05 mm off). It is 20–25 % faster. It is
byte-for-byte the same on macOS and Linux, and its overlays are pure
DeviceGray (C = M = Y = 0). It adds two wheels (fontTools, pypdfium2: 9.2 MB
download on Linux x86_64) and no system package. The 669 MB of apt packages it
replaces go away.

**Crest glyphs: vendor Noto Serif JP SemiBold** (`NotoSerifJP-SemiBold.otf`,
noto-cjk Serif 2.003, the official Japanese subset of the very face Inkscape
uses today; 6.31 MB, +5.37 MB in the wheel).

Runner-up: the same with resvg (resvg-py) as the rasteriser. It works, but it
is slower and fails V-3 on one case (see the results table). The PDF is the
same either way.

What the user gives up, and decides (Q-6): the PDF text becomes outlines, so it is no
longer searchable or copyable. And two of the soft targets are missed: the
flat case's peak memory (288 MB against Inkscape's 110 MB) and the slim image
(42 % of before, unpacked, against a 40 % target).

## 1. Candidates

Phase 1 = desk research + P-1 (wheel closure), P-2 (import, `ldd` /
`otool -L`), P-4 (licences). Phase 2 = prototype + every criterion. P-1/P-2
outputs: [run/p1-matrix.txt], [run/p2-phase1-{amd64,arm64,macos}.txt]
(`proto/phase1/`). Every P-1 set includes menkyo's own `pillow numpy scipy`.

| # | candidate | verdict | phase | reason (criterion, evidence) |
|---|---|---|---|---|
| 1 | **fontTools outlines + own PDF writer + pypdfium2 raster** | **recommended** | 2 | passes every hard criterion; results below |
| 2 | fontTools outlines + own PDF writer + **resvg-py** raster | viable (runner-up) | 2 | V-3 FAIL on C-3 (IoU 0.960 < 0.98): resvg-py 0.5 keeps the aspect ratio when given both pixel dimensions, so a per-side rounded box comes out a pixel short, and its raster sits ~0.4 px off (V-1 PNG offset −0.42 px). 1.8× slower than pdfium on the Mac (C-1 4.4 s against 2.5 s). On macOS it links `/usr/lib/libiconv.2.dylib` (ships with macOS, but not on P-2's literal list) |
| 3 | skia-python 144.1 (raster, SkPDF, SVG module) | rejected | 1 | **P-2**: `ImportError: libEGL.so.1`; `ldd` shows `libEGL.so.1`, `libGL.so.1`, `libexpat.so.1` *not found* (amd64 and arm64); it also bundles its own fontconfig |
| 4 | pypdfium2 as the rasteriser | part of #1 | 2 | — |
| 5 | Pillow `ImageDraw` / `ImageFont` | rejected | 1 (desk) | already a dependency, passes P-1/P-2, but it is raster only: Pillow writes a PDF as an embedded image (**F-2**: the flat PDF must have zero images), and `ImageDraw.polygon` is not antialiased (**V-5** jagged edges on crest and guides). The Linux wheel has no raqm (`features.check("raqm")` is False), which would not matter for single glyphs |
| 6 | reportlab 5.1.0 (PDF) | rejected | 1 (desk) | passes P-1/P-2/P-4 (BSD), but its `TTFont` refuses CFF fonts (`reportlab/pdfbase/ttfonts.py:247`, "postscript outlines are not supported"), and the crest mincho is CFF. With outlines it would only replace our ~215-line writer with a dependency |
| 7 | svglib 2.3.2 + reportlab | rejected | 1 (desk) | LGPL-3.0-or-later (acceptable as a wheel), same CFF limit, text resolved by family name through reportlab's registry, +5 packages (`lxml`, `cssselect2`, `tinycss2`, `webencodings`, `charset-normalizer`) |
| 8 | fpdf2 2.8.9 | rejected | 1 (desk) | LGPL-3.0-only (acceptable as a wheel); `fpdf.svg` imports a subset of SVG, and we would still walk `document()` ourselves; no gain over #1's writer |
| 9 | pikepdf 10.17.0 + hand-written content streams | rejected | 1 | P-1: no resolution for 3.13 on `aarch64-apple-darwin` at uv's default macOS target (its arm64 wheels need a newer macOS tag); MPL-2.0 is fine. It would only serialise objects our writer already writes. Kept as a **test tool** (qpdf check) |
| 10 | a small writer of our own | part of #1 | 2 | — |
| 11 | skia-python's PDF backend | rejected | 1 | as #3 (**P-2**) |
| 12 | CairoSVG 2.9.1 / cairocffi | rejected | 1 | **P-2**: `OSError: no library called "cairo-2" was found` in the slim image (system cairo) |
| 13 | rsvg-convert | rejected | 1 (desk) | **P-1/P-2**: a system program (librsvg), no wheel |
| 14 | PyMuPDF 2.0 | rejected | 1 | **P-4**: AGPL-3.0 (or commercial). P-1/P-2 pass; 68.9 MB wheel |
| 15 | Ghostscript as a wheel | rejected | 1 | **P-2**: PyPI `ghostscript` 0.8.1 is a ctypes binding, `RuntimeError: Can not find Ghostscript library (libgs)`; **P-4**: the binding is GPL-3.0-or-later and Ghostscript AGPL |
| 16 | matplotlib 3.11.2 | rejected | 1 (desk) | cannot draw `document()`'s SVG at all (no SVG input); 9.86 MB wheel plus 7 dependencies for a writer we do not need |

Crest glyph source (G-3, Q-1); fonts from [proto/fetch_fonts.sh](proto/fetch_fonts.sh)
(pinned by tag/commit and sha256), sizes from `proto/fontsizes.py`
[run/fontsizes.txt], crest metrics from `compare.py` on C-5 [run/metrics-cand-crest-*.json]:

| option | file | in the wheel | crest crop SSIM / worst ring centroid | verdict |
|---|---|---|---|---|
| Noto Serif CJK JP SemiBold, whole | `NotoSerifCJKjp-SemiBold.otf` 24.73 MB | +20.42 MB | 0.9898 / 0.024 mm | viable; 4× the size for no gain |
| **Noto Serif JP SemiBold, official JP subset** | `NotoSerifJP-SemiBold.otf` 6.31 MB, 16,726 code points | **+5.37 MB** | 0.9898 / 0.024 mm | **recommended** |
| Noto Serif JP (Google Fonts, variable) instanced at wght 600 | `NotoSerifJP-wght600.ttf` 8.08 MB | +4.55 MB | 0.9896 / 0.024 mm | viable; a derived file we would have to generate; 0.8 MB smaller |
| a subset (JIS X 0208 + X 0213 + kana) | 3.60 MB, 8,611 code points | +3.05 MB | — | rejected: covers only 7,371 of Yuji Boku's 8,013 code points and drops 𠮷, so it is a poor fallback (Q-2), and `crest_ring` / `[art]` are free text |
| an OFL mincho on PyPI | none found (`noto-serif-jp`, `notoserifjp`, `noto-serif-cjk`, `fonts-noto-cjk`, `font-noto-serif-jp`, `noto-fonts-cjk`, `notofonts`: PyPI 404) | — | — | rejected |
| subset at build time from a font the user supplies | — | — | — | rejected: contradicts "pip only, deploy anywhere" |
| Yuji Boku for the ring | already vendored | 0 | — | rejected: contradicts DECISIONS "The crest ring stays mincho"; would need the user's consent |

## 2. Results

Recommended route = #1, measured on macOS arm64 unless the row says otherwise.
Runner-up = #2. Its PDF is byte-identical to #1's, so every PDF criterion
(F-*) and every 600 dpi crop criterion (computed from the PDF) are the same as
#1's. Only the raster criteria differ.

| criterion | threshold | recommended (#1) | verdict | runner-up (#2) | verdict |
|---|---|---|---|---|---|
| **P-1** wheels, full closure | 6 required combos resolve | 9/9 with `uv pip compile --only-binary :all:` and 9/9 with `pip download` (file names below). `pypdfium2 5.14.0` ships `macosx_13_0_arm64` only, so the macOS tag must be 13.0+ (5.9.0 was the last `11_0` wheel) | PASS | 9/9 (`resvg-py 0.5.0`, abi3) | PASS |
| **P-2** Linux, no system libs | imports; no `not found`; renders C-1 C-3 C-4 C-5 | `ldd`: 0 not found, 0 other libraries in pypdfium2 and fontTools; amd64 container renders all four; `dpkg -l … \| grep -c` = 0; no `/usr/share/fonts`. Pillow/numpy/scipy (already dependencies) link `libz.so.1` from the base image, which is on the manylinux whitelist | PASS | `ldd` clean (amd64, arm64) | PASS |
| **P-2** macOS | `otool -L` allowed list only | pypdfium2, fontTools: none outside the list | PASS | resvg-py: `/usr/lib/libiconv.2.dylib` (a macOS system library) | PASS, with that note |
| **P-2** Linux arm64 (reported) | — | renders C-1 C-3 C-4 C-5 [run/p2arm64.txt]; ldd clean | reported | ldd clean | reported |
| **P-3** no system fonts | no `/Font` in the PDF; identical with system fonts | no font is ever looked up by name: `norender.Face` opens two **files**, and the PDFs have **no `/Font` resources**. C-1 with and without `fonts-noto-cjk`: PNG and PDF **byte-identical** | PASS | `skip_system_fonts=True`, and text is already outlines | PASS |
| P-3 macOS vs Linux (soft) | ≈ 1 LSB | C-1, C-4, C-5 PNG: **pixel-identical** (max \|Δ\| 0, 0 % of pixels > 1; the files differ only in zlib bytes); PDF byte-identical | PASS | not measured | — |
| **P-4** licences | MIT-compatible | fontTools MIT; pypdfium2 Apache-2.0 / BSD-3 (docs CC-BY-4.0); in libpdfium: PDFium BSD-3, FreeType (FTL), libjpeg-turbo (IJG + BSD), libpng, zlib, lcms2 (MIT), OpenJPEG (BSD-2), AGG 2.3 (permissive), abseil (Apache-2.0), ICU (Unicode v3, permissive), fast_float, simdutf, llvm-libc (Apache-2.0 with LLVM exception). Fonts OFL-1.1 (below) | PASS | resvg-py MIT (resvg MIT/Apache-2.0) | PASS |
| **G-1** placement (C-4, C-5, 600 dpi) | every glyph ≤ 0.15 mm | 62 glyphs (C-4): worst `name` フ 0.049 mm, median 0.004 mm; C-5: worst ス 0.007 mm; C-4b: worst ー 0.025 mm | PASS | same PDF | PASS |
| **G-2** vertical-text specifics | human check, confirmed by G-1 | checked in the crops: ァ ェ ョ upper right; ー vertical (C-4b, added: C-4's name has no ー); ・ centred; shrunk name at 8.762 mm in both; date 西暦二〇二〇年十月二十日 | PASS | same | PASS |
| **G-3** crest ring | mincho; crop SSIM ≥ 0.95, no region; centroid ≤ 0.15 mm | Noto Serif JP SemiBold; crest SSIM 0.9898, largest region 0 mm²; worst ring centroid 0.024 mm. `traced_glyphs = true` renders (throwaway 道, crest SSIM 0.9897) | PASS (equivalent face: user to accept, Q-1) | same | PASS |
| **G-4** missing glyph | fallback or clear error, non-zero exit | **Today**: Inkscape silently draws 𠮷 in Noto Serif CJK JP SemiBold, exit 0. **Candidate**: error policy prints `the character 𠮷 (U+20BB7) is not in Yuji Boku Regular (YujiBoku-Regular.ttf)…`, exit 1, exactly one `error` event and no `done`. Fallback policy draws it from the crest mincho, like today (name crop SSIM 0.9995 against Inkscape). The example config and the three stand-in names use no character Yuji Boku lacks (it covers all 6,355 JIS X 0208 kanji) | PASS | same | PASS |
| **G-5** stroke weight | ink per column ±3 % (C-4) | no synthetic emboldening in the reference: `fc-match -v "Yuji Boku:weight=180"` has no `embolden` and weight 80, and `pdffonts` lists Yuji Boku as `CID TrueType` (not Type 3). Ink per column: heading +0.01 %, name +0.87 %, rank +0.02 %, formula +0.03 %, date 0.00 %, art −0.01 %, dōjō 0.00 %, title +0.03 %, signer +0.03 %, motto +0.01 % | PASS | same | PASS |
| **G-6** missing / corrupt font file | clear error naming the file, exit ≠ 0, one `error` | missing: `font file not found: …/YujiBoku-Regular.ttf (body face, Yuji Boku)`; truncated: `… is unreadable or corrupt: ValueError: table 'glyf' runs past the end of the file` (crest: `table 'CFF '`); exit 1, one `error` event, before any progress or file | PASS | same | PASS |
| **V-1** page, PDF by pdfium, 150 dpi | SSIM ≥ 0.98 flat / ≥ 0.97 inked; MAD ≤ 2.0 | C-1 0.99971 / 0.072; C-3 0.99972 / 0.070; C-4 0.99969 / 0.071; C-4b 0.99972 / 0.069; C-5 0.99972 / 0.059; offsets ≤ 0.02 px | PASS | same PDF | PASS |
| V-1 direct PNG (reported) | — | C-1 0.99812 / 0.197; C-3 0.99859 / 0.168; C-4 0.99971 / 0.065; C-5 0.99980 / 0.050; C-8 0.99849 / 0.249 | reported | C-1 0.99901 / 0.153; C-3 0.99766 / 0.263; C-4 0.99887 / 0.164; C-5 0.99841 / 0.157; C-8 0.99844 / 0.276; offsets ≈ −0.4 px | reported |
| **V-2** crops, 600 dpi | SSIM ≥ 0.95; no region > 0.3 mm² | lowest crop SSIM: crest 0.9898 (every case), C-4 name 0.9939; every other crop ≥ 0.9959. Largest \|Δ\| > 64 region: **0 mm² in every crop**. Method: sub-pixel alignment (applied above 0.1 px) **and** a 3×3 (0.127 mm) opening | PASS | same PDF | PASS |
| **V-3** text layer | size ±1 px; bbox ±0.05 mm; IoU ≥ 0.98; alpha ±2 %; graded ±0.01, ±2 pp | C-1: 7299×3733 = Inkscape's; bbox off by ≤ 0.0006 mm; IoU 0.9945; alpha +0.055 %; graded mean 0.97559 vs 0.97538 (+0.0002); share < 0.9: 6.584 vs 6.687 % (−0.10 pp). C-3: 7305×3733 = Inkscape's; ≤ 0.0008 mm; IoU 0.9944; +0.035 %; +0.0001; +0.05 pp | PASS | C-1 IoU 0.9912; **C-3 IoU 0.9598** | **FAIL** (C-3) |
| V-3 `--supersample` | 1–4 works; 4×: pixmap, memory | works 1–4, unchanged flag. 4×: a **29196 × 14932** greyscale pdfium bitmap; whole run 4.3 s, peak **0.96 GB**. Inkscape 4×: 15.6 s, peak **4.08 GB** (arm64 Docker) [run/timing-ss4.tsv] | PASS | not measured | — |
| **V-4** ink colour | ΔE2000 ≤ 2 | solid interior median RGB (17, 17, 17) in both, ΔE2000 0.00. Overlay PNGs transparent (alpha 0–255). Proof PNG opaque white, as the contract says; **but today's proof PNG is transparent** (Inkscape's C-5 alpha 0–255), see Risks | PASS | same colour | PASS |
| **V-5** looks good | V-1..V-4 pass; no defect at 600 dpi; the user's verdict | developer's check of every crop sheet: no missing or substituted glyph, no wrong face or rotation, no halo or ragged edge, no jagged edges, no raster where Inkscape has vector. **The user's verdict is pending** (section 6) | pending the user | — | — |
| **F-1** page | 1190.55 × 841.89 pt, one page, no rotation | `[0 0 1190.551 841.89]`, 1 page, `/Rotate` 0 | PASS | same | PASS |
| **F-2** vector stays vector | flat/proof: 0 images; inked: 1 + SMask | C-4, C-5: 0 image XObjects; C-1, C-3: one 7299×3733 (7305×3733) DeviceGray image with a DeviceGray `/SMask` | PASS | same | PASS |
| **F-3** text | embedded font or outlines | **outlines**: no `/Font` in any page; not searchable or copyable (Q-6) | PASS | same | PASS |
| **F-4** other viewers | qpdf check clean; SSIM ≥ 0.95; ink in text bbox ±0.02 | `check_pdf_syntax()` (qpdf's check): no problems, all PDFs. Lowest SSIM: pdfium 0.9977, Ghostscript 10.00 0.9965, poppler 22.12 0.9954, `sips` 0.9964, Quartz (CoreGraphics) 0.9969; ink difference ≤ 0.0020 everywhere (gs on C-4) [run/viewers.json] | PASS | same PDF | PASS |
| F-5 PDF size (soft) | flag > 1.5× or > 5 MB | C-1 533 KB (Inkscape 795, 0.67×); C-3 506 (759, 0.67×); C-4 92 (75, **1.23×**); C-4b 91 (75, 1.22×); C-5 72 (72, 1.01×). None flagged | reported | same | reported |
| **F-6** overlay text DeviceGray | `g`/`G`, gray image + gray SMask, no RGB group; inkcov C=M=Y=0 | C-1, C-3, C-4: only `g`/`G` operators, DeviceGray image and SMask, **no page group**. `gs -sDEVICE=inkcov`: C-1 `0.00000 0.00000 0.00000 0.03244`, C-3 `0 0 0 0.03036`, C-4 `0 0 0 0.03883`. Crest and rings are `g`/`G` too. Proof: guides `RG` (their colours), the rest gray. Today, for contrast: a `/DeviceRGB` page group, `rg`/`RG`, inkcov C-1 `0.04152 0.04249 0.04249 0.03251` | PASS | same PDF | PASS |
| **N-1** PNG size | 4961×3508 at 300, as Inkscape at 150; pHYs | 4961×3508 (300 dpi), 2480×1754 (C-8, = Inkscape's); pHYs 11811 px/m (299.999 dpi, as Inkscape) and 5906 px/m at 150 (Inkscape writes 5905; both 150 dpi to 0.01 %) | PASS | same sizes | PASS |
| N-2 PNG size (soft) | flag > 1.5× | C-1 465 KB (Inkscape 645); C-3 445 (616); C-4 393 (502); C-5 459 (489); C-8 187 (260). None flagged | reported | not measured | — |
| **R-1** determinism | same PNG bytes; PDF equal bar dates/ID | C-1, C-4: PDF and PNG **byte-identical without normalising** (no dates, no ID). Inkscape for context: PNG identical; PDF identical once `/CreationDate` etc. are removed (pikepdf, `static_id`) | PASS | not measured | — |
| S-1 footprint (soft) | report | replaces **173 apt packages, 669.2 MB** installed (with ghostscript: 192 / 724.6 MB). Adds fontTools 4.68.0 + pypdfium2 5.14.0: download 9.22 MB (Linux x86_64), 9.16 MB (aarch64), 6.68 MB (macOS); installed 36.6 MB (Linux) / 25.0 MB (macOS); plus the crest font 6.31 MB. menkyo wheel **5.15 → 10.53 MB** | reported | resvg-py 1.41 MB instead of pypdfium2 | reported |
| S-2 slim image (soft) | after ≤ 40 % of before | unpacked (`du -sx /`): before **989 MB**, after **415 MB** = **42 %**; compressed (`docker save`): 464 → 146 MB = 31 %. What remains is mostly numpy + scipy + Pillow (234 MB), which `ink.py` needs | **target missed** by 2 points (unpacked) | — | — |
| S-3 time (soft, arm64 Docker, median of 3) | candidate / Inkscape ≤ 1.25 | process wall: C-1 3.08 / 3.78 s = **0.81**; C-4 0.63 / 0.86 s = **0.74**. Stages, C-1: text 0.48 (0.78), ink 1.67 (1.69), pdf 0.33 (0.48), png 0.30 (0.58) s; C-4: pdf 0.05 (0.19), png 0.26 (0.39) s, Inkscape in brackets | PASS | macOS native, same Mac: C-1 4.4 s vs #1's 2.5 s; C-4 0.62 vs 0.19 s | reported |
| S-4 memory (soft) | ≤ the Inkscape route, ≤ 2 GB | cgroup `memory.peak`, median: C-1 **955 MB** vs 916 MB (1.04×); C-4 **288 MB** vs 110 MB (2.6×). Both far below 2 GB. C-1's peak is menkyo's own `ink.ink_layer` (~820 MB, the same in both routes); C-4's is the 4961×3508 page bitmap plus Python's numpy/scipy | **target missed** (≤ Inkscape) | not measured | — |
| K-1 compatibility | stated | see section 4 | — | — | — |

### P-1: resolved wheel files (recommended route)

`proto/wheels.sh` (`pip download --only-binary=:all:` under each Python, with
explicit tags; [run/wheels.txt]):

```
3.11 mac            fonttools-4.68.0-cp311-cp311-macosx_10_9_universal2.whl numpy-2.4.6-cp311-cp311-macosx_14_0_arm64.whl pillow-13.0.0-cp311-cp311-macosx_11_0_arm64.whl pypdfium2-5.14.0-py3-none-macosx_13_0_arm64.whl scipy-1.17.1-cp311-cp311-macosx_14_0_arm64.whl
WHEELS_TABLE_PLACEHOLDER
```

`uv pip compile --only-binary :all: --python-platform {aarch64-apple-darwin,
x86_64-manylinux_2_28, aarch64-manylinux_2_28} --python-version {3.11,3.12,3.13}`
resolves all 9 for #1 and #2 ([run/p1-matrix.txt]).

### P-4: fonts, Reserved Font Names, and what the real build must ship

| font | licence | Reserved Font Name | subsetting / instancing / outlining |
|---|---|---|---|
| Yuji Boku (vendored) | OFL-1.1, "Copyright 2021 The Yuji Project Authors" | **none** | outlines in a PDF are a document, not the Font Software: no obligation (the NOTICE already says so) |
| Noto Serif JP SemiBold (noto-cjk Serif 2.003) | OFL-1.1, noto-cjk `Serif/LICENSE` | **none** (no copyright/RFN header line) | shipped unmodified; no RFN to trigger |
| Noto Serif JP (Google Fonts) instanced | OFL-1.1, "Copyright 2012 Google Inc." | **none** | instancing makes a Modified Version: allowed, must stay OFL; no RFN to trigger |

The real build must:

- add `src/menkyo/fonts/NotoSerifJP-SemiBold.otf` with its licence beside it;
- give `NOTICE` a section for it, worded like Yuji Boku's (OFL-1.1, no
  Reserved Font Name);
- note in `METADATA`/README where it came from (noto-cjk tag `Serif2.003`,
  sha256 `116d06c2…a53d`);
- adjust the `NOTICE` sentence "the bundled font" to "the bundled fonts".

## 3. Decision, in one place

- **Renderer:** #1. fontTools outlines from font *files*, a ~215-line SVG
  subset → PDF writer in the package, pypdfium2 for every raster.
  `document()` stays the single source.
- **Crest glyph source:** vendor `NotoSerifJP-SemiBold.otf` whole (+5.37 MB
  wheel). The ring then looks as it does today (crest SSIM 0.990 against the
  real Noto Serif CJK JP SemiBold, ring centroids within 0.024 mm).

## 4. Risks and compatibility (D-1.4, K-1)

**What changes for the CLI and the portal (K-1).** Each item is the user's call
(CLAUDE.md).

- **CLI flags: unchanged.**
- **`--json` events, stage keys and totals: unchanged.** The prototype drives
  menkyo's real `_Progress`: `text`, `ink`, `pdf`, `png` with the same
  `_stages()` totals. The real build must announce `pdf` *before* building
  the PDF. The prototype first did it after, which counted 0.3 s of PDF work
  as `ink`.
- **`-f svg`: unchanged.** The intermediate SVG keeps its `<text>`
  elements, plus `-textlayer.png`. Without Inkscape such an SVG still shows
  Yuji Boku only where the font is installed, as today. An outlined SVG is
  available for free (`outline_svg`) if the user wants it (Q-6).
- **`--supersample`: keeps 1–4 and the same meaning.** The *reason* for the
  cap (cairo's 32767 px) is gone. pdfium's limit is a 2³¹-byte bitmap; the
  4× text layer is 436 MB greyscale. The flag's help text, the error message
  and DECISIONS ("Output, and the supersampling cap") must be reworded.
  Memory at 4× falls from 4.08 GB to 0.96 GB.
- **`--clean` and the `.fontconfig` clean-up:** `.fontconfig` is no longer
  written, and its `rmtree` becomes dead code.
- **`paths.require_tool`, `paths.tool_env`, `paths.system_font_dirs`,
  `_EXTRA_BIN`, `_INSTALL_HINT`, `_font_env()`:** all unused once `--press`
  goes too (`plain-white`). Remove them, together with DECISIONS' "Installed-copy
  behaviour … Homebrew … searched for the tools".
- **Test fakes and golden assertions:** `tests/fakes/fake_tool.py` (fake
  `inkscape` and `gs`) and the golden and regression assertions on tool argv
  (`regression/golden_lib.py`, `golden/manifest.json`) no longer apply.
  **The golden SVGs stay intact**, because `document()` is unchanged. The new
  route is deterministic and byte-identical across macOS and Linux (R-1,
  P-3), so goldens can become real PDF/PNG hashes rendered in plain
  `uv run pytest`, on the Mac, without Docker. That is a stronger suite than
  today's. (A pdfium upgrade may change PNG bytes; pin it, and fall back to
  SSIM when bumping.)
- **"PDF embeds Yuji Boku" checks (F-3):** `pdffonts … | grep -i yuji` in
  `tests/acceptance/test_ac_render.py`, `tests/acceptance/test_ac_wheel.py`
  and `.github/workflows/package.yml` must change. Their purpose (a font
  left out of the wheel fails the release) is better served by G-6: a
  missing font file fails the render with exit 1. Assert that, plus "no
  `/Font`, glyph paths present".
- **The SVG files:** unchanged.

**Risks.**

1. **The writer is new code.** It handles only what `document()` emits
   today. The prototype silently ignores unknown elements. The real build
   must *refuse* any element, attribute or path command it does not handle
   (e.g. arcs, `<use>`, `clipPath`, opacity, CSS `style=`), so a future
   layout change fails loudly instead of printing wrongly.
2. **Ordering with `plain-white` (Q-7).** `border.py` and the coloured
   variants need clipping and colour, and `--press` needs Ghostscript (AGPL,
   a system program). None of these is in the spike. Building this before
   `plain-white` means writing and testing a renderer for code that is about
   to be deleted. **Recommendation: build after `plain-white`.**
3. **Missing glyphs (Q-2).** The prototype raises at `outline_svg`, after the
   first progress event, and leaves `.work/` behind. The real build should
   check every character against the font cmaps in `main()`, before the first
   event: the name, rank, date and the config strings `[art]`, `[dojo]`,
   `crest_ring`, signer and motto. With several awards nothing is then written
   before the error, and `.work/` must be cleaned on failure too.
4. **Proof PNG background.** The contract says proof PNGs are "opaque white,
   as today". The measured reference C-5 PNG is transparent (alpha 0–255,
   because `render()` passes no background for proof). The prototype writes
   it opaque, which is what the contract asks for. Keep today's or the
   contract's? (A one-line choice; flagged so it is not changed by
   accident.)
5. **pypdfium2 is a moving binary.** It is a ctypes binding over
   pdfium-binaries' build of Chromium's PDFium, released often. Pin it
   (`==`) and bump deliberately. 5.14 needs macOS 13 or later.
6. **Memory for the flat variants** rises from 110 to 288 MB (S-4). This is
   harmless against the portal's 2 GB, and fixable if wanted: render into a
   Pillow-owned buffer, or in bands.
7. **Text not searchable or copyable** in the PDFs (Q-6). Today's PDFs carry
   ToUnicode maps. Nobody has said they rely on that.
8. **The slim image stays above 40 %** of today's (42 %) because of
   numpy + scipy (needed by `ink.py`), not because of anything this item
   adds.
9. **The inked overlay's raster sits up to 1 px (600 dpi, 0.045 mm) apart
   from Inkscape's on C-3.** Inkscape renders the layer at exact 600 dpi and
   stretches it to the bbox; we map the bbox onto the pixel grid exactly.
   This is far inside every threshold and invisible, but it is why C-3's
   crops show a sub-pixel offset.
10. **dojo-portal image:** once it pins the new wheel it can drop `inkscape
    fontconfig fonts-noto-cjk fonts-noto-cjk-extra` (and, after
    `plain-white`, `ghostscript`). Until then nothing breaks, because the new
    wheel does not use them.

## 5. Effort for the real build (*estimate*, developer-days)

| part | what | days |
|---|---|---|
| renderer module | `src/menkyo/render.py`: outlines, strict SVG-subset → PDF writer, pdfium raster for the PNG and the text layer; replace `_inked_text_image`, `render`, `_font_env`; announce stages before their work; clean `.work/` on failure | 2.0 |
| font handling | vendor `NotoSerifJP-SemiBold.otf` + licence + NOTICE; `Face` loading with the G-6 errors; the up-front cmap check in `main()` (G-4, with the user's Q-2 choice); drop `paths.require_tool`/`tool_env`/`system_font_dirs` | 1.0 |
| tests | unit tests for the writer (paths, transforms, colours, refusal of unknown SVG); rework golden/regression (no fakes; hash or SSIM goldens of real renders); acceptance tests for G-4, G-6, F-6, R-1; rewrite the `pdffonts` checks | 2.5 |
| Docker test image | `tests/docker/Dockerfile`: drop Inkscape, Ghostscript, poppler and fonts (keep one Linux run of the suite); `scripts/test-docker.sh` stays | 0.5 |
| workflow | `.github/workflows/package.yml`: no apt step; smoke test asserts a render without system packages | 0.5 |
| docs | README (install: no Inkscape), DECISIONS (new entry; rework "The font is vendored…", "Output, and the supersampling cap", "Ink density" (no cairo), "Installed-copy behaviour"), `pyproject.toml` dependencies and comment, `tests/README.md` | 1.0 |
| **total** | after `plain-white`; add ~2 days if it lands first (clipPath, colour, press) | **7.5** |

## 6. For the user to judge

Open each pair in [compare/](compare/) ([index](compare/index.md)). Left or
first is Inkscape today, right or second is the candidate. On the crop sheets
the third panel is the difference × 4 in red (white = identical).

| case | images | what to look at | verdict (acceptable / not, note) |
|---|---|---|---|
| C-1 dan overlay, inked | [side by side](compare/C-1_overlay_side-by-side.png), [crops](compare/C-1_crops.png) | the sumi grading on 段位免状 and 右授与ス; edges of the inked strokes; the crest | |
| C-3 shihan overlay | [side by side](compare/C-3_overlay_side-by-side.png), [crops](compare/C-3_crops.png) | ジョン・ドウ with small ョ; no grade column | |
| C-4 dan overlay-flat, long name | [side by side](compare/C-4_overlay-flat_side-by-side.png), [crops](compare/C-4_crops.png) | the shrunk name, ァ ェ ・, 十段, the date in kanji | |
| C-4b (added) long vowel ー | [side by side](compare/C-4b_overlay-flat_side-by-side.png), [crops](compare/C-4b_crops.png) | ー drawn vertical in ピーター | |
| C-5 proof | [side by side](compare/C-5_proof_side-by-side.png), [crops](compare/C-5_crops.png) | dashed guides, the blank date grid, the crest ring lettering (Noto Serif **JP** SemiBold against today's Noto Serif **CJK JP** SemiBold: Q-1) | |
| C-8 `--dpi 150` | [side by side](compare/C-8_overlay_side-by-side.png) | same sheet at half resolution | |
| C-9 𠮷, fallback policy | [side by side](compare/C-9-fallback_overlay-flat_side-by-side.png), [crops](compare/C-9-fallback_crops.png) | 𠮷 drawn in the mincho in both, as Inkscape does today (Q-2) | |
| traced crest glyph | [crops](compare/C-5-traced-glyph_crops.png) | `traced_glyphs = true` still works (the square is a throwaway stand-in for 道) | |

## Open questions, with the evidence

- **Q-1 Crest font.** Recommend **Noto Serif JP SemiBold, the official JP
  subset, whole** (+5.37 MB). It is the same design as today's face (the
  crest crop is identical to the whole CJK OTF's: SSIM 0.9898 both, ring
  centroids 0.024 mm). It covers 16,726 code points, including all of JIS
  X 0208 and 𠮷. The whole CJK font costs 4× more for nothing. A subset
  saves 2.3 MB but breaks free-text `crest_ring`/`[art]` and the fallback.
  The variable Google Fonts instance is equally good and 0.8 MB smaller, but
  is a file we would generate.
- **Q-2 Missing glyphs.** Today a missing character is silently set in the
  mincho, exit 0 (C-9). Recommend **an error by default**, checked up front:
  a recipient's name is "the one word on the sheet its owner will study
  hardest" (DECISIONS), and a mincho kanji among brush kana is visibly wrong.
  Yuji Boku covers all of JIS X 0208, so in practice this only hits rare
  characters like 𠮷. Then the portal can show the message and the dōjō can
  pick a variant (吉). The fallback is implemented and measured if the user
  prefers today's behaviour.
- **Q-4 Print check.** The PDFs are not just similar but geometrically the
  same: glyphs within 0.05 mm, the same ink grading (mean 0.9756 against
  0.9754), and every viewer honours the soft mask. On screen that is enough
  to say it *looks* the same. Two printer-relevant things do change, though:
  the overlays are now pure K (C = M = Y = 0, where today they carry 3–4 %
  C, M and Y), and the inked raster is no longer inside an RGB transparency
  group. Recommend **one real A3 print of C-1 from each route** before the
  first certificate is issued with the new one. It costs two sheets and
  tests exactly what changed.
- **Q-6 Compatibility.** Recommended answers: `--supersample`, the `-f svg`
  side raster and the `--json` totals **do not change**. Only
  `--supersample`'s explanation changes. **Flat-PDF text becomes outlines**
  (not searchable or copyable): acceptable, recommend yes, since these are
  print assets. **`-f svg` keeps `<text>`** (unchanged, and the golden SVGs
  stay intact). Outlined SVG could be added later if anyone opens these
  SVGs without the font.
- **Q-7 Ordering.** Build after `plain-white` (risk 2).

## Deviations from the contract, and notes

- **Added case C-4b.** C-4's name contains no ー, so G-2's "ー rotated"
  would have gone untested. C-4b is C-4 with ピーター・ファン・デル・フェルデン.
- **`--supersample 4` case `C-1-ss4`** in `proto/cases.py`, for V-3.
- **The proof PNG background** (risk 4): the contract's "as today" does not
  match today.
- **P-2's allowed-library list:** Pillow, numpy and scipy (already menkyo's
  dependencies) resolve `libz.so.1` from the base image on Linux, and Pillow
  links `/usr/lib/libbz2.1.0.dylib` on macOS. These predate this item, and
  libz is on the manylinux policy whitelist. The candidate's own additions
  link nothing outside the list.
- **S-2 sizes:** with Docker 29's containerd image store,
  `docker image inspect .Size` was not stable: it returned 153 MB, then
  602 MB, for the same image. The spike therefore reports the unpacked
  filesystem (`du -sx /` in the image) and `docker save`, both for
  `linux/amd64`.
- **The runner-up** was measured on the criteria where it differs from #1
  (the raster: P-*, V-1 PNG, V-3, time). Its PDF is #1's byte for byte.
- **F-4 Preview/Quartz:** `sips -z 1754 2480` and a 20-line CoreGraphics
  renderer (`proto/quartz_render.swift`) agree (SSIM 0.9993 on C-4). Both
  are reported.
- **The bug the comparison caught.** A first prototype wrote glyph matrices
  to 3 decimals: 11.5/1000 became 0.012, so every 11.5, 12.5 and 8.762 mm
  column was 4 % off. G-1 and G-5 flagged it at once (date ink −8.5 %,
  worst glyph 0.38 mm). It is fixed (full precision), and the numbers above
  are after the fix. It shows these two metrics catch real errors.

## User decisions (2026-10-28)

The user evaluated the comparison images and decided:

- **Go ahead** with the recommended route (fontTools outlines, our own PDF
  writer, pypdfium2), built after `plain-white`.
- **Q-1 crest font:** ship Noto Serif JP SemiBold **whole** (+5.4 MB),
  not a subset and not the 20 MB pan-CJK file.
- **Q-2 missing glyphs:** stop with an error naming the character, checked
  up front, so the portal can ask for a replacement ("names are usually
  katakana anyway"). No silent fallback.
- **Q-4 print:** print tests are ongoing on the user's side; consider it
  accepted and adjust later if needed.
- **Q-6:** the PDF does not need to be searchable; outlines are fine. The
  other compatibility answers stand as recommended (`--supersample`, `-f svg`
  with `<text>`, and the `--json` totals unchanged).

Note: the spike's final rerun of `proto/reproduce.sh` ended with exit 1 and
was stopped by the orchestrator when it stalled; the results and images above
come from the earlier complete runs. The real build re-measures everything.
