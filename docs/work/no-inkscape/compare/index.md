# Comparison images (D-2)

Inkscape 1.2.2 (Debian bookworm, with `fonts-noto-cjk-extra`) on the left or
first; the recommended candidate (fontTools outlines, our own PDF writer,
pdfium) on the right or second. Stand-in data only, from
`src/menkyo/example.toml`. Made by `proto/compare.py`; `proto/reproduce.sh`
regenerates them (step `publish`).

- `*_side-by-side.png`: the whole page, as each route **wrote its PNG**,
  composited on white and shown at 100 dpi.
- `*_crops.png`: 600 dpi crops of **each route's PDF rasterised by pdfium**.
  Each crop is three panels: Inkscape, candidate, and |difference| × 4 in red
  (white means identical). Long name columns are split into pieces of about
  70 mm.

| file | what to look at |
|---|---|
| `C-1_overlay_side-by-side.png` | dan, inked overlay (ヤン・ヤンセン, 二段): sumi grading, crest |
| `C-1_crops.png` | inked heading, name, 二段, date, crest at 600 dpi: halo or ragged edges on the graded text |
| `C-3_overlay_side-by-side.png` | shihan licence as an overlay: no grade column, ジョン・ドウ |
| `C-3_crops.png` | small ョ upper right in its cell; crest ring |
| `C-4_overlay-flat_side-by-side.png` | flat vector text, long shrunk name (アレクサンドル・ファン・デル・フェルデン, 十段) |
| `C-4_crops.png` | small ァ ェ, ・ centred, shrunk name the same size, 十段, date in kanji numerals |
| `C-4b_overlay-flat_side-by-side.png` | added case: C-4 with ピーター・ファン・デル・フェルデン, for ー |
| `C-4b_crops.png` | ー turned 90° (vertical) in the name column |
| `C-5_proof_side-by-side.png` | proof: dashed guides, blank date grid, calligrapher zones |
| `C-5_crops.png` | dashed guide rectangles in the date grid; crest |
| `C-8_overlay_side-by-side.png` | C-1 at `--dpi 150`, PNG only |
| `C-9-fallback_overlay-flat_side-by-side.png` | 𠮷 (not in Yuji Boku): Inkscape's silent fallback against the candidate's *fallback* policy |
| `C-9-fallback_crops.png` | 𠮷 in the name column: both routes draw it in the Noto mincho (Q-2) |
| `C-5-traced-glyph_crops.png` | `traced_glyphs = true` with a throwaway traced 道 (a square, not a real glyph) in the crest ring (G-3) |
