# Certificate design — decisions log

Why the certificates and the generator read as they do. One dated entry per
decision, kept only while it still explains something in the current design:
decisions that were later overridden are deleted rather than annotated, and so
are the alternatives that were considered and not taken. What remains is what
someone adapting this needs in order to change it safely.

The generator was written for one dōjō. Nothing here names that dōjō, its art,
its teachers, or the certificate this one replaces; where a decision turned on
something particular to the school, the entry says so without saying which.

## 2026-09-05 — Brief

- **Faithful traditional**: cream stock, engraved border, mon at top centre,
  vertical brush columns. The sheet reads as a Japanese document, not as club
  marketing, and every later decision defers to that.
- **Japanese only**, no Latin anywhere on the sheet.
- **A3 landscape**, 420 × 297 mm — large enough for comfortable brushwork.
- **Three slots left for the calligrapher**: rank, name, date. Everything else
  is printed. Each is optionally printable; see below.
- **Issuing authority: the dōjō, one signatory** — the art, the dōjō, then the
  signatory's office and name. The office is deliberately one that claims
  nothing beyond this dōjō: a title asserting the lineage of the art as a
  whole, or a federation's name, would tie the document to standing the school
  may not have or may not keep.
- **Date: 西暦 (Gregorian), kanji numerals.** Era years would silently
  invalidate a stock of printed sheets at the next era change, and the dōjō is
  European.
- **Crest: mon inside a double ring** — the dōjō on the lower arc, the art on
  the upper, no Latin.
- **Signature: printed name, stamped seal.** Clear space below the printed
  name takes a real vermilion seal, so every copy is an original.
- **Verify the dōjō's name in kanji; never read it off the logo.** Display
  lettering is rotated and distorted to follow its arc: a first attempt
  transcribed two of four glyphs wrong. What settles it is the attested
  *reading* matching the school's own romanisation. Confirm the signatory's
  katakana with the signatory, too — these get printed on every document the
  dōjō will ever issue.

## 2026-09-05 — Three documents, each headed by its award

- **A printed heading column names the award**, top right at 18 mm, where a
  賞状 carries its title: 段位免状 / 師範免許状 / 錬士免許状, against 右授与ス
  for grades and 右免許ス for licences. Documents that differ only in their
  formula — 授与 against 免許, two characters in one column — are
  indistinguishable at arm's length; headings that look nothing alike are what
  makes the set read apart.
- **Crest geometry is vector**, normalised to the outer ring's centreline
  radius: a *yotsume-bishi*, four lozenges at N/E/S/W each pierced by a
  smaller one, `fill-rule="evenodd"`.
- **The ring kanji are typeset, not traced.** Display lettering distorted to
  fit an arc is barely legible at 38 mm, and tracing it puts a second arc on
  top of the first. Tracing stays available (`traced_glyphs`) for a school
  whose own lettering is worth the trade.
- **Proportions from a traditional 賞状, rebalanced for a single signatory.**
  With one signature column the printed block would otherwise sit far right
  and leave a third of the sheet empty.

## 2026-09-05 — The drawn border

`src/border.py`, so the dōjō is not held hostage to sourcing Japanese stock.
`*-full.pdf` is the same document with it.

- **The motif language is taken from commercial 賞状用紙, not copied from it.**
  Those borders are a commercial pattern; every line here is generated.
  Phoenix plumes with herringbone barbs on a visible spine, peacock
  eye-feathers, and a chain of florets and berry sprigs along the inner edge.
- **Clipped to the band**, plumes drawn long and trimmed to an annulus, or
  they spill off the sheet and the frame reads as loose feathers rather than
  one deliberate ribbon.
- **Density is the whole problem, and the answer is fewer, fatter, more
  densely barbed**: 13 mm spacing, plumes 2.1 × the band width at 34°, barbs
  every 0.72 mm, spine at twice the barb weight. Each feather keeps its
  silhouette while overlapping its neighbours like shingles. Tighter spacing
  reads as a woven mat with no feathers legible; longer, shallower plumes
  tangle into scratchy noise.
- **Mirror-symmetric about the vertical axis.** A directional motif run
  continuously around a rectangle pinwheels, which reads as careless on a
  formal document. A small pierced lozenge, echoing the mon, closes each seam.
- **Sepia `#8a6a33`**, close to aged 賞状用紙 and subordinate to the black
  brush it frames. The crest drops 8 mm here to clear the band's inner rule.
- **Colour conversion differs per route.** Overlays get `-K.pdf` (DeviceGray)
  so black prints as 100 % K; the full artwork gets `-CMYK.pdf`, since
  greyscaling would throw the border colour away.
- **Cream both ways.** `full` prints on cream stock with no background;
  `full-cream` prints the tint too, for white stock. The first always looks
  better — a printed "paper colour" is flat, and toner sits on top of it.

## 2026-09-05 — Calligraphic typeface

- **Body face: Yuji Boku** (佑字 木), Kinuta Font Factory, SIL OFL. Genuinely
  brush-written kaisho — real stroke modulation, visible brush entry and exit,
  the asymmetry of a hand. Ten Japanese faces were set at real size against
  hand-brushed reference to pick it.
- **If you swap the face, check it at 40 mm, not at 12.** Finer brush faces
  model *kasure*, the dry-brush break-up of a running-out brush; it passes at
  body size and reads as ragged at the size of the award formula. Watch ス in
  particular.
- **The crest ring stays mincho.** A mon is a carved seal, not brushwork, and
  the firmer face holds together at 5 mm where a brush face goes soft.
- **The font is vendored, not installed.** `_font_env()` writes a fontconfig
  file including the system config plus `fonts/`, handed to Inkscape via
  `FONTCONFIG_FILE`: reproducible anywhere, and nothing on the user's machine
  changes.
- **The authentic route not taken**: have the calligrapher brush the fixed
  columns once, scan at 600 dpi and potrace. Worth doing if a dōjō has the
  calligrapher's time — only the source of the glyphs changes, not the layout.

## 2026-09-05 — Ink density: sumi rather than flat black

`src/ink.py` grades the ink from glyph geometry alone, on the physical
relationship that a lifting brush lays down both a narrower stroke and less
ink. Uniform black is what no brush ever does.

- **The measure is local stroke thickness** — the diameter of the largest disc
  that fits inside the stroke and covers the point. The cheap alternatives are
  worse in specific, visible ways: distance-to-edge darkens every stroke's
  spine and embosses the page, and a medial axis propagated outward by nearest
  neighbour leaves grey scratches where nearest-ridge regions meet. The
  union-of-discs sweep has no seams because it is a union, not a partition.
- **Normalised per connected stroke**, so the 40 mm formula and the 12 mm
  authority block read as one hand rather than the small columns greying out.
- **Thinness is the signal, not the rate of narrowing.** In real brushwork a
  thin stroke *is* lighter, because less brush is touching the paper.
- **`MIN_DENSITY = 0.76`**, swept against hand-brushed reference. Real sumi is
  very black, with its variation in a narrow band near the tips.
- **The density field is extended outward by nearest-inside value before it is
  blurred or upsampled.** Without that step the field's out-of-stroke value
  bleeds inward and rings every glyph with a pale halo — the edges then look
  rough, and it is not a sampling problem. Edge alpha is 122.9 against a
  predicted 126.8; the remainder is the intended grading.
- **The crest is excluded** — a seal pressed in one go must not fade at its
  thin points.
- **Cost: the text becomes a raster.** Border, crest and page stay vector; the
  text layer is a 600 dpi greyscale image with an alpha soft mask, cropped to
  its bounding box, about 1 MB. Verify through Ghostscript, not just Inkscape:
  an embedded soft mask is exactly what silently breaks in PDF.
- **`*-flat` variants exist for both routes** — solid black, pure vector. A
  home laser halftones grey and some commercial RIPs mishandle soft masks.
  This is the one thing to check on a real print before committing to ink.

## 2026-09-05 — Output, and the supersampling cap

- **Default: `overlay` and `full-cream`, PDF only** — six files for the three
  awards. The overlay is the print asset; full-cream shows the finished sheet.
  Everything else is behind `--variants`, `--formats` and `--press`, because
  building it all unconditionally produced 75 files and buried the two that
  matter.
- **Intermediates in `build/.work/`**, deleted afterwards with the fontconfig
  cache, so `build/` can be wiped freely — hence `--clean`. One wrinkle: an
  inked SVG references its raster by relative path, so `--formats svg` copies
  the raster out alongside it.
- **`--supersample` is capped at 4 and defaults to 1.** Cairo, which Inkscape
  renders through, refuses image surfaces wider than 32767 px and the A3 text
  block is 6622 px at 600 dpi, so 5× and beyond abort in the renderer whatever
  the machine has. It defaults to 1 because cairo antialiases analytically
  rather than by sampling: 2× differs from 1× by 0.0121/255 and 4× by 0.0123,
  saturating immediately and never becoming visible, at double and quadruple
  the build time. The knob is exposed because it is honest to, not because it
  helps.
- The text layer renders with `--export-area-drawing` and is placed from
  Inkscape's own bbox query, in CSS px (hence the 96/25.4 conversion), which
  is what makes any supersampling affordable; Pillow's decompression-bomb
  guard has to be lifted for our own multi-hundred-megapixel render.

## 2026-09-05 — Printing the three hand slots

`--rank`, `--name` and `--date` each print what the calligrapher would
otherwise brush. The hand-brushed sheet is what you get without them, because
it looks better and it is what a calligrapher is for.

- **`--name` takes its own column, right of the award**, where a 賞状 puts the
  recipient: read after the heading, before the body. 殿 by default. 16 mm
  nominal, shrunk to fit `AWARDEE_MAX_H` — a 13-character name lands at
  14.2 mm and still clears the border, and European names in katakana run
  long, so this is not a rare case.
- **The transcription is the dōjō's call, not the tool's.** A Dutch *Geert*
  could be ヘールト, ゲールト or フェールト; the hard G has no Japanese
  equivalent. Flagged in the README rather than guessed at in code — it is the
  one word on the sheet its owner will study hardest.
- **`--rank` turns numbers and romaji into kanji**: `2` or `nidan` → 二段, up
  to 10, and **1 → 初段, never 一段**. Plain numerals rather than the formal
  大字, the commoner modern practice on issued certificates; anything
  unrecognised passes through literally, so `--rank 弐段` gets the formal form
  and `--rank 師範` makes one flag serve the licences too. Out of range is
  refused rather than silently producing nonsense.
- **`--date` takes ISO or `today`.** The year goes digit by digit —
  西暦二〇二六年 — as 西暦 requires; month and day are spoken numbers, 十二月
  and 三十一日. A printed date is set solid; a blank one keeps its slots spaced
  as a grid to write into, and the day needs **three** of them, since 二十一
  through 三十一 are three characters and that is most of the month.
- **Filenames carry rank and name, not the date.** Those identify *which*
  document and must not collide — a person collects several grades over the
  years. A corrected date should replace the file, not sit beside the wrong
  one.

## 2026-09-05 — The licences have no grade column

- **A dan diploma states a grade; a licence names its award in the heading and
  has nothing further to say.** With the name printed and no grade, a reserved
  column left a hole and stranded the name against the right edge, so the
  column is absent rather than empty — no printed grade, no guide rectangle on
  the proof.
- **Columns are spaced, not pinned.** `right_columns()` spreads whatever
  columns exist evenly between heading and formula, so the layout closes up on
  its own: with a grade it reproduces the hand-tuned 327 / 296, without one
  the name centres at 308.
- **`--rank` overrides it**, restoring the column and restating the title
  beside the name.
- The award declares its own answer (`grade_column`), so a fourth document
  added later does not touch the layout code.

## 2026-09-05 — Purple menkyo, and a precept column

**Menkyo gets purple, dan keeps sepia.** In the art this was built for, the
shihan belt is the one uniquely purple rank — a real, non-arbitrary reason to
separate the *class* of menkyo documents from dan diplomas. The hex is not
invented: sampled from the school's own dark ink, then matched in lightness
and saturation to the sepia so neither reads heavier on the page — `#8a336f`.
Affects only `full` and `full-cream`; the overlay route's border is bought
stock. Verified through Ghostscript's CMYK conversion, not just Inkscape. A
school with no such colour in its tradition should leave every award the same
colour: the point is that the distinction means something.

**A precept column was added** — `[motto] text`, empty unless configured. A
precept is the school's to word; the generator only finds it a place to stand.

- **On every document**, not the licences only: a precept is foundational to
  the art, the same reasoning that puts the art's name on every crest, not a
  status distinction between grades and licences.
- **Its own column.** The crest ring already carries eight characters across
  two arcs at 38 mm, and a dozen more would overcrowd it or force enlarging
  the crest. The printed block — art, dōjō, office, signatory — is a fixed
  ceremonial reading order, and a precept, being what the school holds to
  rather than a term of the award, reads oddly spliced into it.
- **Placed in the open margin left of the signature column** (`X_MOTTO = 57`),
  a ~40 mm strip every other layout pass had left empty. The column runs
  143 mm at 11 mm per character with no collision against the seal — checked
  by measuring every existing column's extent, not by eyeballing the render.

## 2026-09-06 — Translations for recipients, one file per award

`docs/*-explained.md`: each document glossed line by line in reading order,
every phrase with its kanji, reading and meaning.

- **Written for the person who receives the certificate**, not for anyone
  making one: no typeface, no colours, no character sizes, no command lines,
  no reference to this log, nothing about what is deliberately absent.
- **One file per award, each self-contained.** The repeated sections are
  deliberate duplication — someone handed only the shihan licence should not
  need the dan file beside it to read their own certificate.
- **The crest section gives the yotsume-bishi's traditional sense** — "four
  eyes", watchfulness against harm from every direction — not only its
  geometry. A school with a crest of its own has more to say than the shape.
- **Written by hand, not generated**, unlike everything else here. They
  describe the meaning of fixed strings in the configuration, so if that
  wording changes these files need a matching edit; they will not follow.

## 2026-09-06 — Made publishable

The generator went into a public repository where other dōjō may use it, which
meant separating the tool from the school and then from the documentation.

- **Everything identifying a school lives in TOML** (`src/config.py`,
  `config/example.toml`): the art, the dōjō, the crest ring, the signatory,
  the precept, the paper measurements, the awards themselves. Layout constants
  stayed in code — those are typography, not identity.
- **The shipped default names nobody**, using 〇〇 throughout, so a clone
  produces a correctly typeset certificate that grants nothing.
- **`dojo.toml` in the root is picked up automatically and git-ignored**, so
  the local build needs no flag while the identity stays out of the
  repository. It follows that a fresh clone falls back to the placeholders:
  keep a copy of `dojo.toml` somewhere else.
- **Also git-ignored: `crest/`, `build/`, `ref/`** — traced crest glyphs are a
  school's own lettering, `build/` holds certificates with real recipients'
  names, and `ref/` held photographs of other people's credentials.
- **The traced-glyph hook is generic**: it looks for `crest/<character>.svg`
  and returns None if absent, with no school baked in.
- **MIT for the code, with two carve-outs** (`NOTICE`): the bundled font stays
  under the SIL OFL, and crests, school names and teachers' names are nobody's
  to grant. The default crest is the yotsume-bishi, a public-domain kamon.
- **The recipient explainers are templates.** They explain in full everything
  the unconfigured generator prints; for the four things that are
  configuration they describe only the form, each marked with an **"If you are
  adapting this document"** block. The precept is configuration and is quoted
  nowhere.
- **An AI-authorship note at the top of the README.** The code and
  documentation here were written by a language model; the certificates are
  real and printable. Worth stating plainly to anyone deciding whether to
  trust the repository.

## 2026-09-06 — The default build fills every slot

Anonymising the generator left it demonstrating almost nothing: a fresh clone
printed a heading, a formula, 〇〇流柔術, 〇〇道場 and 師範, and empty space
where the grade, recipient, signatory, date and precept go. That is the
correct *print* asset and a poor *first impression* — most of the layout only
exists once something is in those columns.

- **Stand-ins, not emptiness.** `config/example.toml` fills what it left
  blank: `crest_ring = "〇〇道場"`, `signer.name = "山田太郎"` (the Japanese
  John Doe, the name on every form) and `motto.text = "柔能制剛"`, "the soft
  controls the hard" — a classical maxim old enough to be nobody's words. Real
  characters, because 〇〇 everywhere fills the columns without showing what
  they look like filled.
- **`[sample]` supplies what `--rank`, `--name` and `--date` fall back to**
  when the flag is absent — 5, ジョン・ドウ, `today`. The three slots are CLI
  flags rather than configuration, so a first run with no arguments needed
  somewhere for its defaults to come from that is visible and editable.
- **`''` clears one for a run** (`-n '' -r '' -d ''`). A fallback you cannot
  turn off is a trap: the blank sheet is what most users actually print. A
  flag being absent and a flag being empty therefore mean different things,
  which is why the resolution is a helper (`_fallback`) rather than an
  argparse default.
- **A sample grade is gated on `grade_column`.** Applied uniformly it put 五段
  on the shihan licence, whose heading has already named its award and which
  deliberately has no grade column. An explicit `--rank` stays unconditional —
  that is what `--rank 師範` relies on.
- **Specimens are tagged `-sample`** via `[sample] suffix`, so a first build
  writes `dan-overlay-sample.pdf` and says on its face what it is. Naming a
  recipient or grade takes the derived tag instead; otherwise every recipient
  would collide on `-sample`, the exact thing the derived tag prevents.
- **The section is documented as something to delete**, not to edit — the one
  part of the example config a real `dojo.toml` should not have. With it gone
  the three flags behave exactly as before and the slots are blank again.

## Open

- **Source the 賞状用紙.** Still the preferred route: `border` and
  `safe_inset` under `[paper]` are placeholders (22 mm / 38 mm) until measured
  against a real sheet. Japanese A3 stock is not easy to buy in Europe —
  likely an import, and it must be **横型** (landscape); much of what is sold
  is portrait and the border will not rotate.
- **Test the drawn border on the actual printer** before committing to it. Its
  strokes are 0.11–0.22 mm. A laser at 600 dpi holds them; an inkjet on
  absorbent uncoated stock may thicken them and darken the band. If so, raise
  `density` — wider spacing — rather than thinning the strokes.
- **Confirm the katakana transcription of any recipient's name** with the
  recipient before printing.
