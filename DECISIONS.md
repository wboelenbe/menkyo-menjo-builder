# Certificate design – decisions log

Why the certificates and the generator read as they do. One dated entry per
decision, kept only while it still explains something in the current design:
decisions that were later overridden are deleted rather than annotated, and so
are the alternatives that were considered and not taken. What remains is what
someone adapting this needs in order to change it safely.

The generator was written for one dōjō. Nothing here names that dōjō, its art,
its teachers or the certificate this one replaces; where a decision turned on
something particular to the school, the entry says so without saying which.

## 2026-09-05 – Brief

- **Faithful traditional**: cream stock, engraved border, mon (crest) at top
  centre, vertical brush columns. The sheet reads as a Japanese document, not
  as club marketing, and every later decision defers to that.
- **Japanese only**, no Latin anywhere on the sheet.
- **A3 landscape**, 420 × 297 mm – large enough for comfortable brushwork.
- **Three slots left for the calligrapher**: rank, name, date. Everything else
  is printed. Each is optionally printable; see below.
- **Issuing authority: the dōjō, one signatory** – the art, the dōjō, then the
  signatory's office and name. The office is deliberately one that claims
  nothing beyond this dōjō: a title asserting the lineage of the art as a
  whole, or a federation's name, would tie the document to standing the school
  may not have or may not keep.
- **Date: 西暦 (Gregorian), kanji numerals.** Era years would silently
  invalidate a stock of printed sheets at the next era change, and the dōjō is
  European.
- **Crest: mon inside a double ring** – the dōjō on the lower arc, the art on
  the upper, no Latin.
- **Signature: printed name, stamped seal.** Clear space below the printed
  name takes a real vermilion seal, so every copy is an original.
- **Verify the dōjō's name in kanji; never read it off the logo.** Display
  lettering is rotated and distorted to follow its arc: a first attempt
  transcribed two of four glyphs wrong. What settles it is the attested
  *reading* matching the school's own romanisation. Confirm the signatory's
  katakana with the signatory, too – these get printed on every document the
  dōjō will ever issue.

## 2026-09-05 – Three documents, each headed by its award

- **A printed heading column names the award**, top right at 18 mm, where a
  賞状 (award certificate) carries its title: 段位免状 / 師範免許状 / 錬士免許状, against 右授与ス
  for grades and 右免許ス for licences. Documents that differ only in their
  formula – 授与 against 免許, two characters in one column – are
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

## 2026-09-05 – The drawn border

`src/border.py`, so the dōjō is not held hostage to sourcing Japanese stock.
`*-full.pdf` is the same document with it.

- **The motif language is taken from commercial 賞状用紙, not copied from it.**
  Those borders are a commercial pattern; every line here is generated.
  Phoenix plumes with herringbone barbs on a visible spine, peacock
  eye-feathers and a chain of florets and berry sprigs along the inner edge.
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
  better – a printed ‘paper colour’ is flat, and toner sits on top of it.

## 2026-09-05 – Calligraphic typeface

- **Body face: Yuji Boku** (佑字 木), Kinuta Font Factory, SIL OFL. Genuinely
  brush-written kaisho (regular script) – real stroke modulation, visible
  brush entry and exit, the asymmetry of a hand. Ten Japanese faces were set
  at real size against hand-brushed reference to pick it.
- **If you swap the face, check it at 40 mm, not at 12.** Finer brush faces
  model *kasure*, the dry-brush break-up of a running-out brush; it passes at
  body size and reads as ragged at the size of the award formula. Watch ス in
  particular.
- **The crest ring stays mincho.** A mon is a carved seal, not brushwork, and
  the firmer face (mincho, the printed serif style) holds together at 5 mm
  where a brush face goes soft.
- **The font is vendored, not installed.** `_font_env()` writes a fontconfig
  file including the system config plus `fonts/`, handed to Inkscape via
  `FONTCONFIG_FILE`: reproducible anywhere, and nothing on the user's machine
  changes.
- **The authentic route not taken**: have the calligrapher brush the fixed
  columns once, scan at 600 dpi and potrace. Worth doing if a dōjō has the
  calligrapher's time – only the source of the glyphs changes, not the layout.

## 2026-09-05 – Ink density: sumi rather than flat black

`src/ink.py` grades the ink from glyph geometry alone, on the physical
relationship that a lifting brush lays down both a narrower stroke and less
ink. Uniform black is what no brush ever does.

- **The measure is local stroke thickness** – the diameter of the largest disc
  that fits inside the stroke and covers the point. The cheap alternatives are
  worse in specific, visible ways: distance-to-edge darkens every stroke's
  spine and embosses the page, and a medial axis propagated outwards by nearest
  neighbour leaves grey scratches where nearest-ridge regions meet. The
  union-of-discs sweep has no seams because it is a union, not a partition.
- **Normalised per connected stroke**, so the 40 mm formula and the 12 mm
  authority block read as one hand rather than the small columns greying out.
- **Thinness is the signal, not the rate of narrowing.** In real brushwork a
  thin stroke *is* lighter, because less brush is touching the paper.
- **`MIN_DENSITY = 0.76`**, swept against hand-brushed reference. Real sumi (brush
  ink) is very black, with its variation in a narrow band near the tips.
- **The density field is extended outwards by nearest-inside value before it is
  blurred or upsampled.** Without that step the field's out-of-stroke value
  bleeds inwards and rings every glyph with a pale halo – the edges then look
  rough, and it is not a sampling problem. Edge alpha is 122.9 against a
  predicted 126.8; the remainder is the intended grading.
- **The crest is excluded** – a seal pressed in one go must not fade at its
  thin points.
- **Cost: the text becomes a raster.** Border, crest and page stay vector; the
  text layer is a 600 dpi greyscale image with an alpha soft mask, cropped to
  its bounding box, about 1 MB. Verify through Ghostscript, not just Inkscape:
  an embedded soft mask is exactly what silently breaks in PDF.
- **`*-flat` variants exist for both routes** – solid black, pure vector. A
  home laser halftones grey and some commercial RIPs mishandle soft masks.
  This is the one thing to check on a real print before committing to ink.

## 2026-09-05 – Output, and the supersampling cap

- **Default: `overlay` and `full-cream`, PDF only** – six files for the three
  awards. The overlay is the print asset; full-cream shows the finished sheet.
  Everything else is behind `--variants`, `--formats` and `--press`, because
  building it all unconditionally produced 75 files and buried the two that
  matter.
- **Intermediates in `build/.work/`**, deleted afterwards with the fontconfig
  cache, so `build/` can be wiped freely – hence `--clean`. One wrinkle: an
  inked SVG references its raster by relative path, so `--formats svg` copies
  the raster out alongside it.
- **`--supersample` was capped at 4 and defaulted to 1**, until it was
  removed (see ‘Supersampling removed’, 29 October 2026). Cairo, which
  Inkscape
  renders through, refuses image surfaces wider than 32767 px and the A3 text
  block is 6622 px at 600 dpi, so 5× and beyond aborted in the renderer
  whatever the machine had. It defaulted to 1 because cairo antialiases
  analytically rather than by sampling: 2× differed from 1× by 0.0121/255 and
  4× by 0.0123, saturating immediately and never becoming visible, at double
  and quadruple the build time.
- The text layer renders with `--export-area-drawing` and is placed from
  Inkscape's own bbox query, in CSS px (hence the 96/25.4 conversion), so the
  raster covers the text and not the empty page around it. Pillow's
  decompression-bomb guard is lifted for that render: it is our own, not
  untrusted input. While the supersampling knob existed, the crop was what
  made it affordable at all.

## 2026-09-05 – Printing the three hand slots

`--rank`, `--name` and `--date` each print what the calligrapher would
otherwise brush. The hand-brushed sheet is what you get without them, because
it looks better and it is what a calligrapher is for.

- **`--name` takes its own column, right of the award**, where a 賞状 puts the
  recipient: read after the heading, before the body. 殿 (the honorific after
  the name) by default. 16 mm
  nominal, shrunk to fit `AWARDEE_MAX_H` – a 13-character name lands at
  14.2 mm and still clears the border, and European names in katakana run
  long, so this is not a rare case.
- **The transcription is the dōjō's call, not the tool's.** A Dutch *Geert*
  could be ヘールト, ゲールト or フェールト; the hard G has no Japanese
  equivalent. Flagged in the README rather than guessed at in code – it is the
  one word on the sheet its owner will study hardest.
- **`--rank` turns numbers and romaji into kanji**: `2` or `nidan` (romaji:
  Japanese in Latin letters) → 二段, up to 10, and **1 → 初段, never 一段**.
  Plain numerals rather than the formal 大字 (the numerals of legal documents,
  such as 弐), the commoner modern practice on issued certificates; anything
  unrecognised passes through literally, so `--rank 弐段` gets the formal form
  and `--rank 師範` makes one flag serve the licences too. Out of range is
  refused rather than silently producing nonsense.
- **`--date` takes ISO or `today`.** The year goes digit by digit –
  西暦二〇二六年 – as 西暦 requires; month and day are spoken numbers, 十二月
  and 三十一日. A printed date is set solid; a blank one keeps its slots spaced
  as a grid to write into, and the day needs **three** of them, since 二十一
  through 三十一 are three characters and that is most of the month.
- **Filenames carry rank and name, not the date.** Those identify *which*
  document and must not collide – a person collects several grades over the
  years. A corrected date should replace the file, not sit beside the wrong
  one.

## 2026-09-05 – The licences have no grade column

- **A dan diploma states a grade; a licence names its award in the heading and
  has nothing further to say.** With the name printed and no grade, a reserved
  column left a hole and stranded the name against the right edge, so the
  column is absent rather than empty – no printed grade, no guide rectangle on
  the proof.
- **Columns are spaced, not pinned.** `right_columns()` spreads whatever
  columns exist evenly between heading and formula, so the layout closes up on
  its own: with a grade it reproduces the hand-tuned 327 / 296, without one
  the name centres at 308.
- **`--rank` overrides it**, restoring the column and restating the title
  beside the name.
- The award declares its own answer (`grade_column`), so a fourth document
  added later does not touch the layout code.

## 2026-09-05 – Purple menkyo, and a precept column

**Menkyo gets purple, dan keeps sepia.** In the art this was built for, the
shihan (master instructor) belt is the one uniquely purple rank – a real,
non-arbitrary reason to separate the *class* of menkyo (licence) documents
from dan diplomas. The hex is not
invented: sampled from the school's own dark ink, then matched in lightness
and saturation to the sepia so neither reads heavier on the page – `#8a336f`.
Affects only `full` and `full-cream`; the overlay route's border is bought
stock. Verified through Ghostscript's CMYK conversion, not just Inkscape. A
school with no such colour in its tradition should leave every award the same
colour: the point is that the distinction means something.

**A precept column was added** – `[motto] text`, empty unless configured. A
precept is the school's to word; the generator only finds it a place to stand.

- **On every document**, not the licences only: a precept is foundational to
  the art, the same reasoning that puts the art's name on every crest, not a
  status distinction between grades and licences.
- **Its own column.** The crest ring already carries eight characters across
  two arcs at 38 mm, and a dozen more would overcrowd it or force enlarging
  the crest. The printed block – art, dōjō, office, signatory – is a fixed
  ceremonial reading order, and a precept, being what the school holds to
  rather than a term of the award, reads oddly spliced into it.
- **Placed in the open margin left of the signature column** (`X_MOTTO = 57`),
  a ~40 mm strip every other layout pass had left empty. The column runs
  143 mm at 11 mm per character with no collision against the seal – checked
  by measuring every existing column's extent, not by eyeballing the render.

## 2026-09-06 – Translations for recipients, one file per award

`docs/*-explained.md`: each document glossed line by line in reading order,
every phrase with its kanji, reading and meaning.

- **Written for the person who receives the certificate**, not for anyone
  making one: no typeface, no colours, no character sizes, no command lines,
  no reference to this log, nothing about what is deliberately absent.
- **One file per award, each self-contained.** The repeated sections are
  deliberate duplication – someone handed only the shihan licence should not
  need the dan file beside it to read their own certificate.
- **The crest section gives the yotsume-bishi's traditional sense** – ‘four
  eyes’, watchfulness against harm from every direction – not only its
  geometry. A school with a crest of its own has more to say than the shape.
- **Written by hand, not generated**, unlike everything else here. They
  describe the meaning of fixed strings in the configuration, so if that
  wording changes these files need a matching edit; they will not follow.

## 2026-09-06 – Made publishable

The generator went into a public repository where other dōjō may use it, which
meant separating the tool from the school and then from the documentation.

- **Everything identifying a school lives in TOML** (`src/config.py`,
  `config/example.toml`): the art, the dōjō, the crest ring, the signatory,
  the precept, the paper measurements, the awards themselves. Layout constants
  stayed in code – those are typography, not identity.
- **The shipped default names nobody**, using 〇〇 (the Japanese placeholder,
  ‘so-and-so’) throughout, so a clone produces a correctly typeset certificate
  that grants nothing.
- **`dojo.toml` in the root is picked up automatically and git-ignored**, so
  the local build needs no flag while the identity stays out of the
  repository. It follows that a fresh clone falls back to the placeholders:
  keep a copy of `dojo.toml` somewhere else.
- **Also git-ignored: `crest/`, `build/`, `ref/`** – traced crest glyphs are a
  school's own lettering, `build/` holds certificates with real recipients'
  names, and `ref/` held photographs of other people's credentials.
- **The traced-glyph hook is generic**: it looks for `crest/<character>.svg`
  and returns None if absent, with no school baked in.
- **MIT for the code, with two carve-outs** (`NOTICE`): the bundled font stays
  under the SIL OFL, and crests, school names and teachers' names are nobody's
  to grant. The default crest is the yotsume-bishi, a public-domain kamon
  (family crest).
- **The recipient explainers are templates.** They explain in full everything
  the unconfigured generator prints; for the four things that are
  configuration they describe only the form, each marked with an **‘If you are
  adapting this document’** block. The precept is configuration and is quoted
  nowhere.
- **An AI-authorship note at the top of the README.** The code and
  documentation here were written by a language model; the certificates are
  real and printable. Worth stating plainly to anyone deciding whether to
  trust the repository.

## 2026-09-06 – The default build fills every slot

Anonymising the generator left it demonstrating almost nothing: a fresh clone
printed a heading, a formula, 〇〇流柔術, 〇〇道場 and 師範, and empty space
where the grade, recipient, signatory, date and precept go. That is the
correct *print* asset and a poor *first impression* – most of the layout only
exists once something is in those columns.

- **Stand-ins, not emptiness.** `config/example.toml` fills what it left
  blank: `crest_ring = "〇〇道場"`, `signer.name = "山田太郎"` (the Japanese
  John Doe, the name on every form) and `motto.text = "柔能制剛"`, ‘the soft
  controls the hard’ – a classical maxim old enough to be nobody's words. Real
  characters, because 〇〇 everywhere fills the columns without showing what
  they look like filled.
- **`[sample]` supplies what `--rank`, `--name` and `--date` fall back to**
  when the flag is absent – 5, ジョン・ドウ, `today`. The three slots are CLI
  flags rather than configuration, so a first run with no arguments needed
  a visible, editable place for its defaults to come from.
- **`''` clears one for a run** (`-n '' -r '' -d ''`). A fallback you cannot
  turn off is a trap: the blank sheet is what most users actually print. A
  flag being absent and a flag being empty therefore mean different things,
  which is why the resolution is a helper (`_fallback`) rather than an
  argparse default.
- **A sample grade is gated on `grade_column`.** Applied uniformly it put 五段
  on the shihan licence, whose heading has already named its award and which
  deliberately has no grade column. An explicit `--rank` stays unconditional –
  that is what `--rank 師範` relies on.
- **Specimens are tagged `-sample`** via `[sample] suffix`, so a first build
  writes `dan-overlay-sample.pdf` and says on its face what it is. Naming a
  recipient or grade takes the derived tag instead; otherwise every recipient
  would collide on `-sample`, the exact thing the derived tag prevents.
- **The section is documented as something to delete**, not to edit – the one
  part of the example config a real `dojo.toml` should not have. With it gone
  the three flags behave exactly as before and the slots are blank again.

## 2026-09-06 – A configurable start point for the columns

Asked to move the printed columns down for a more generous top margin, and to
make that adjustable rather than hand-picking new constants once.

- **`[paper] text_drop`**, a fraction of the page height added to every
  column's starting point (`Y_HEADING`, `Y_RANK`, `Y_VERB`, `Y_BLOCK`) at
  render time. A fraction of page height rather than an absolute mm figure,
  matching how the request was framed (‘a tenth of the page’) and keeping the
  knob meaningful if the page size ever stops being a hardcoded A3 constant.
  Applied uniformly so the columns move as one rigid group and keep their
  hand-tuned relative spacing – not scaled per-column, which would have
  reopened every proportion this log already settled.
- **The Config dataclass itself defaults to `0.0`**, so a `dojo.toml`
  predating this feature is unaffected until its owner opts in; `0`
  reproduces the original layout exactly, columns starting right under the
  crest.
- **Checked against every column, not just the one that was asked about.**
  `vcol` centres glyph *i* at `y0 + i*size`, so a column's rendered extent is
  `(n - 0.5) * size`, not `n * size` – worth remembering before estimating any
  of these by hand. The one column worth checking is the date **left blank**:
  its fourteen slots are the tallest thing on the sheet, so it is the first to
  reach `safe_inset` as the drop grows. A *printed* date is over 30 mm shorter
  and is never close.
- **Shipped at `0.05`, not the `0.10` first asked for.** At `0.10`, every
  column but the blank date gains 15–60 mm of spare room before `safe_inset`
  – but that one column's last slot lands about 18 mm past it, some 2 mm into
  where a bought sheet's own printed border would sit, at the shipped
  `border` / `safe_inset` (22 mm / 38 mm). At `0.05` the same column clears
  `safe_inset` by a few mm instead of missing it, while still giving the top
  of the sheet visibly more air than `0` did. Halving the request cost
  noticeably less visible effect than it bought back in headroom.
- **Caught while testing: this machine's own `dojo.toml` exists and is picked
  up by default.** A build run without `-c` during this work used it instead
  of `config/example.toml`, rendering real names into `build/`. `dojo.toml`
  being git-ignored means it was never at risk of being committed, but the
  render still happened and was shown before being caught and deleted. Every
  render for this log and its images now pins `-c config/example.toml`
  explicitly; worth remembering whenever this repository is used as its own
  test fixture.

## 2026-10-28 – A package, for the dojo portal

The generator is to become one page of a Django site (dojo-portal) for a few
chosen users. The portal pins a release; it does not vendor this repository.

- **A wheel on GitHub Releases.** `src/` became the package `menkyo`, with
  the font and `example.toml` inside it as package data. Tagging `v<version>`
  publishes the wheel; the portal names its URL and `uv.lock` pins the hash.
  The repository is public, so no credentials are involved, and the portal's
  image needs no git.
- **Why a package at all, and not top-level modules.** The old flat modules
  were importable as `config`, `paths`, `service` – and the portal has its
  own `config` package. Under one name, nothing collides.
- **The wheel is the generator and its command only.** The Tk window, the
  FastAPI front end, PyInstaller and Docker build on it from this repository;
  the portal wants none of FastAPI or Tk.
- **A command, not an API.** The portal runs `menkyo … --json` in a
  subprocess. The generator keeps its state in module globals and a render
  can take a couple of GB; a process per certificate keeps both out of the
  web server's workers, and the flags were already the documented contract.
- **Progress, as JSON lines.** A certificate takes tens of seconds, so
  `--json` reports each slow step (`text`, `ink`, `pdf`, `press`, `png`) with
  its number and the total, then the files, then `done` or `error`. The
  stage keys let the portal say it in Dutch; the English label is for
  everyone else. Without `--json` nothing changes on stdout, which
  `service.run_build` parses. The portal reads only stdout, so under
  `--json` every failure ends in one `error` event and exit code 1: a
  rejected flag, a broken TOML and an unwritable `--out` as much as a
  failing Inkscape.
- **A checkout behaves as before; an installed copy looks only at itself.**
  The repository-root `dojo.toml` and `./build` apply only when the package
  sits in a checkout – a `pyproject.toml` naming `menkyo` two levels up, so
  a copy vendored inside another project is not one; installed or frozen,
  it is the per-user folder and `~/Documents/Menkyo`. Traced crest glyphs
  moved from the repository root to a `crest/` beside the configuration that
  switches them on, which is the same place in a checkout and a sensible one
  everywhere else.
- **Packaging is tested by rendering.** The release workflow installs the
  wheel outside the checkout, renders and checks the PDF embeds Yuji Boku,
  so a font left out of the package fails the release and not the portal.

## 2026-10-28 – `xlink:href` for the inked text, for Inkscape 1.2

The inked variants (`overlay`, `full`, `full-cream`) are a chrome SVG with
the graded text placed on it as an `<image>` raster. That element used SVG
2's plain `href`, which Inkscape 1.3 reads and 1.2 silently ignores: on
Debian bookworm and Ubuntu 24.04 – the deploy image, the release runner,
likely the portal – the defaults printed with the crest and no text. The
real renders in the Docker test image caught it; it predates the package.

The image now uses `xlink:href`, which every Inkscape reads, and only the
chrome layer's root `<svg>` declares `xmlns:xlink`. Flat, proof and
text-layer SVGs are byte-for-byte as before; requiring Inkscape 1.3 was the
alternative, and neither of those distributions packages it.

## 2026-10-28 – The command is the product: no app, no web page, no releases

dojo-portal is the only front end there will be, and it runs
`menkyo … --json` in a subprocess. Everything else that built on the package
went.

- **No Mac app, no web front end, no deploy.** The Tk window, the PyInstaller
  `.app`, the Homebrew formula, the FastAPI page and its Docker/Caddy
  deploy, and `service.py`, which turned form values into flags for the
  window and the web page, are deleted. One consumer does not justify four
  ways to install, each with its own paths and tests. The CLI and its
  `--json` events are untouched; what `service.py` checked before calling
  the generator (a 40-character name cap, the grade whitelist, a blank rank
  on licences, always passing `--name= --rank= --date=` so `[sample]` never
  reaches a real certificate) is now the portal's to do.
- **No release flow.** No tag, no GitHub Release, no published wheel. The
  portal is built on the same Mac as this checkout and builds its wheel from
  it with `uv build --wheel`; the version in `pyproject.toml` still says
  which one it has. Publishing would add a step and a place to go stale for
  nobody else to download from.
- **Testing stays as strict.** `origin` is the NAS, so GitHub CI does not run
  on a normal push: the check is the local `uv run pytest` plus
  `scripts/test-docker.sh`, with real renders. The workflow runs the same
  suite and the installed-wheel smoke test when `main` is pushed to the
  `github` remote (and on pull requests there), and publishes nothing.
- **Installed-copy behaviour is kept.** `paths.py` lost only its frozen-app
  branch. An installed wheel still writes to `~/Documents/Menkyo` and reads
  the per-user `dojo.toml`, and Homebrew, MacPorts and `Inkscape.app` are
  still searched for the tools, since a subprocess may not inherit a login
  shell's PATH. `config.save()` stays as the helper for writing a
  `dojo.toml`.

## 2026-10-28 – Plain white paper only

The certificates print on plain white A3 and nothing else: black text and
crest, no frame, no background. The drawn border, the paper tint, the award
colours and the press conversions are gone, and with them the bought-stock
route. This overrides the cream stock and engraved border of the Brief, ‘The
drawn border’, the default and `--press` of ‘Output, and the supersampling
cap’, and the colours of ‘Purple menkyo, and a precept column’; those
entries are left as they were written.

- **Three variants: `overlay`, `overlay-flat`, `proof`.** `full`,
  `full-cream`, `full-flat` and `border.py` are deleted, not deprecated:
  asking for one is the ordinary ‘unknown variant’ error. What remains
  renders exactly as before, byte for byte; the crest keeps its unbordered
  place.
- **The default is `overlay` alone**, as PDF. It is the certificate; there
  is no longer a coloured sheet to look at beside it. A Dutch companion
  sheet is to join it (`## Open`).
- **No `--press`, so no Ghostscript.** It made `-K` and `-CMYK` files for a
  commercial printer, and the `-K` ones of the inked overlay were not even
  K-only. Black on white needs no conversion. The flag is now unknown, the
  `press` stage leaves the `--json` events, and Inkscape is the only program
  the package needs on the host.
- **`colour` in `[[awards]]` is accepted and ignored**, silently, so an
  existing `dojo.toml` keeps working; the example and `config.save()` no
  longer write it. With nothing coloured left to draw, a warning would only
  be noise.
- **`[paper] border` and `safe_inset` stay**, with their defaults, as
  margins on the white sheet: `border` kept clear all round, `safe_inset`
  where the text may begin. The proof draws both. They no longer stand for
  a bought sheet's printed band.
- **A change to the portal's contract, made while nothing depends on it.**
  dojo-portal is not built yet. It should pass `--variants` explicitly, map
  only the stages `text`, `ink`, `pdf`, `png`, and build
  `menkyo-0.2.0-py3-none-any.whl`: the version went to 0.2.0 with this
  change. Its image can drop Ghostscript.

## 2026-10-29 – The ink pass grades the alpha alone

An inked A3 overlay peaked near 1 GB, about 820 MB of it in `ink_layer`,
which carried the full 600 dpi RGBA raster (109 MB a copy at 7299 × 3733)
and float32 copies of it through the grading. The ink is unchanged: the
graded alpha is bit for bit what it was.

- **Only the coverage is kept.** `ink_layer` reads the render, keeps its
  alpha and lets the rest go; the graded raster is rebuilt at the end as
  the ink colour, `#111111`, under the graded alpha. Inkscape's own RGB at
  the antialiased edge (0 to 32 against 17) is not kept: over white that is
  at most 0.91/255, and the colour now says what it means.
- **Coverage × density goes a band of rows at a time**, in the same
  float32 arithmetic as the whole-image product, so no full-size float
  array exists.
- **The distance transforms come a band at a time too** (`ink._edt`).
  SciPy's computes its distances from the nearest-background indices in one
  go, at about 40 bytes a pixel; on the 200 dpi field that made the
  local-thickness sweep the peak. Same arithmetic, so the same values.
- **`--supersample` scaled the alpha alone**, until the flag was removed
  later the same day (see ‘Supersampling removed’). Pillow resizes RGBA
  premultiplied, channel by channel, so the alpha came out as before, and
  the RGB and its premultiplied copy (1.7 GB each at 4×) were never made.
  The `--supersample` rows of the table below are history.

| measured | before | after |
|---|---|---|
| `ink_layer`, C-1 size, peak RSS over a fresh process (Mac) | +1176 MB, 1.67 s | +263 MB (22 %), 1.63 s |
| `--supersample 2`: resize + `ink_layer` (Mac) | +1961 MB, 3.1 s | +740 MB, 2.7 s |
| `--supersample 4`: resize + `ink_layer` (Mac) | +4041 MB, 5.2 s | +2184 MB, 4.3 s |
| whole run, C-1, cgroup `memory.peak` (Docker, median of 3) | 927 MB, 3.8 s | 437 MB (47 %), 3.8 s |
| peak RSS of the `menkyo` process alone (`ink_driver.py`, Inkscape excluded; RSS counts shared pages the cgroup peak does not) | 944 MB | 221 MB (23 %) |
| the same, `ink_layer` replaced by a file copy (the floor) | | 435 MB, 2.1 s |
| `ink_layer` in that run (Docker, median of 3) | 1.69 s | 1.62 s |
| whole run, `--supersample 2` (Docker) | 1378 MB, 6.9 s | 622 MB, 6.5 s |
| whole run, `--supersample 4` (Docker) | 4092 MB, 15.4 s | 2235 MB, 14.0 s |

The whole run now peaks in Inkscape, not here: with the grading replaced
by a file copy it still reaches 435 MB, so the target of 40 % (370 MB) is
out of reach for the ink pass, and the run sits within 1 % of that floor
(the contract's fallback allows 15 %).

## 2026-10-29 – Supersampling removed

`--supersample` is gone, with every code path behind it: the range check,
the resize of the alpha to the 600 dpi box, and the parameters that carried
the factor. The text layer is rendered at 600 dpi and nothing else, and a
run without the flag writes exactly what it wrote before.

- **Why: it never helped.** Cairo antialiases analytically, so 2× and 4×
  differed from 1× by about 0.012/255 (see ‘Output, and the supersampling
  cap’), at two and four times the build time and up to 2 GB more memory.
  A knob that changes nothing visible is one more thing to explain, test
  and keep working.
- **No shim.** `--supersample` is now an unknown flag like any other: exit
  2 with argparse's ‘unrecognized arguments’, or one `error` event under
  `--json`. dojo-portal never passed it, so its contract is untouched; the
  version stays 0.2.0. A side effect: `--su` used to be ambiguous between
  `--suffix` and `--supersample` and now abbreviates `--suffix`.
- **Nothing to port.** The no-Inkscape renderer (see Open) has no
  supersampling to reproduce: it only has to render the text layer at
  600 dpi, as Inkscape does now.

## 2026-10-29 – Rendered without Inkscape

The package draws the certificates itself, from Python packages alone: no
Inkscape, no fontconfig, no system font and no other program at run time,
on macOS arm64 and Linux x86_64 alike. The route is the one the no-inkscape
spike recommended and the user accepted
([spike.md](docs/work/no-inkscape/spike.md)). It overrides these, which
are left as they were written:

- ‘The font is vendored, not installed’: fontconfig and `FONTCONFIG_FILE`;
- the text-layer bullet of ‘Output, and the supersampling cap’: Inkscape's
  `--export-area-drawing` and its bbox query;
- ‘Cost: the text becomes a raster’, where it says Inkscape;
- ‘Installed-copy behaviour is kept’, where Homebrew, MacPorts and
  `Inkscape.app` are searched for the tools;
- ‘Packaging is tested by rendering’, where the release checks with
  `pdffonts` that the PDF embeds Yuji Boku;
- ‘Plain white paper only’, where Inkscape is the one program needed.

What replaces them:

- **`document()` stays the one description of the sheet**, and its SVG is
  unchanged byte for byte, `-f svg` included, `<text>` and all. What
  Inkscape did with it is now `render.py`: fontTools reads each glyph's
  outline from the font *file*, our own writer turns the small part of SVG
  that `document()` uses into PDF operators and pdfium (pypdfium2) draws
  that PDF for the PNG and for the 600 dpi text layer the ink pass grades.
  Two dependencies are added, `fonttools>=4.68` and `pypdfium2==5.14.0`,
  the second pinned exactly because its raster bytes move between releases.
- **The writer refuses what it does not handle.** An element, attribute,
  transform, colour or path command outside its list (the arc `A` among
  them) ends the run with an error naming it; nothing is silently dropped,
  so a layout change that needs more fails loudly instead of printing
  wrongly. `.work` is removed on every failure, not only on success.
- **The crest face is vendored too: Noto Serif JP SemiBold**, the Japanese
  subset of the face Inkscape used, from noto-cjk `Serif2.003`
  (`SubsetOTF/JP/NotoSerifJP-SemiBold.otf`, 6.31 MB, unmodified, OFL beside
  it as `OFL-NotoSerifJP.txt`). The whole pan-CJK file is four times the
  size for the same ring.
- **Family names map to files.** The SVG still says
  `font-family="Yuji Boku"` and `font-family="Noto Serif CJK JP SemiBold"`;
  `render.FONTS` maps the first to `YujiBoku-Regular.ttf` and the second to
  `NotoSerifJP-SemiBold.otf`. Fonts are opened by path, never looked up by
  family name, so nothing installed on the machine is read. `font-weight`
  selects nothing: each family is one file.
- **The PDF's text is outlines**: filled paths, written inline per glyph,
  with no font in the file. It cannot be searched or copied; these are
  print files, and the user accepted it. One glyph per character at its
  advance width, which is all `document()` sets.
- **The overlays are DeviceGray.** A neutral colour is written as `g`/`G`,
  the inked text is a DeviceGray image with a DeviceGray soft mask and
  there is no page transparency group, so C = M = Y = 0 where Inkscape's
  RGB group carried 3–4 % of each. The proof keeps its coloured guides.
- **A character the fonts lack is an error, not a fallback**, found before
  anything is drawn, written or emptied by `--clean`. Exactly what will be
  drawn is checked: the selected awards only, the honorific only with a
  name, a `[sample]` grade only where there is a grade column, `[art]
  name` against both faces. The message names the character, its `U+`
  code and the flag or key it came from, and asks for a replacement; under
  `--json` it is the one `error` event. A traced `crest/<ch>.svg` stands in
  for the font, and its path data is checked up front as well. `--list` is
  not checked. The writer itself never draws `.notdef`. A missing or
  truncated font file is named the same way, up front: every table's
  extent is checked against the file's size, since fontTools reads lazily.
- **The flat variants render in greyscale.** A page without colour on it
  (`overlay`, `overlay-flat`) is drawn by pdfium in grey and written as an
  LA PNG: the ink, `#111111`, under the alpha that gives the grey drawn,
  which over white is the same pixel. The proof is drawn in RGBA. Every PNG
  stays transparent where nothing is drawn, as before.
- **Nothing large is held whole.** Rasters are drawn and written a band of
  rows (256 KB) at a time by `png.py`, which writes unfiltered rows (they
  deflate as well as Pillow's adaptive filters on this content) and reads
  its own files back the same way. `ink.coverage` reads the LA text layer a
  band at a time, `ink_layer` lets the coverage go while it works out the
  density field and reads it again for the product, and writes its RGBA
  result a band at a time; NumPy and SciPy are imported only when the ink
  is graded. The graded alpha is bit for bit what it was. A side effect of
  banding: pixels differ from a one-piece pdfium draw by at most 2/255,
  scattered, with no seam, and the result is the same every time.
- **The text layer's box** is the exact outline box of the glyphs (curve
  extrema, from fontTools) and its pixel size that box at 600 dpi, rounded
  per side; C-1's is 7299 × 3733 px, as Inkscape's was.
- **Deterministic**: no dates and no IDs in the PDF, so the same command
  writes the same bytes.
- **`--dpi` takes 1 to 2400**, on every run, `--list` and runs without a
  PNG included; anything else is refused with an error (the one `error`
  event under `--json`). Without Inkscape in between, a bad value would
  reach our own code; 2400 dpi is already over a gigapixel on A3, and the
  portal never passes `--dpi`.

Measured on the Mac's native `linux/arm64` Docker (OrbStack), cgroup
`memory.peak` and wall time, median of 3, with
`tests/acceptance/render_without_inkscape/measure.sh`, the same day: before
is 8509b85 with Inkscape 1.2.2 (`Dockerfile.ref`), after is this change in
`menkyo-test`.

| case | before | after |
|---|---|---|
| C-1, overlay, PDF + PNG | 413 MB, 3.65 s | 206 MB, 2.53 s |
| C-1p, overlay, PDF (the portal's run) | 413 MB, 3.02 s | 188 MB, 2.33 s |
| C-4, overlay-flat, PDF + PNG | 104 MB, 0.75 s | 64 MB, 0.34 s |
| C-4p, overlay-flat, PDF | 103 MB, 0.35 s | 59 MB, 0.22 s |
| C-5, proof, PDF + PNG | 102 MB, 0.75 s | 64 MB, 0.38 s |

- C-1 is 22 % of the 933 MB it took before the ink pass was reworked. The
  first run of a fresh source tree reads it cold and peaks higher (up to
  309 MB for C-1); the median is the steady figure.
- The floor of a flat run, in the same image: 25 MB for the imports, 60 MB
  with both fonts open. C-4 renders in 4 MB above that.
- C-1's stages: the checks and opening the fonts 0.12 s, text 0.20 s, ink
  1.68 s, PDF 0.23 s, PNG 0.15 s (the spike's Inkscape run: text 0.78,
  ink 1.69, PDF 0.48, PNG 0.58).
- The `menkyo` process's own peak on the Mac (`ru_maxrss`, which keeps
  pages macOS has not reclaimed): C-1 359 MB, C-4 77 MB.
- The wheel grows from 5.14 to 10.53 MB, nearly all of it the crest font.
  The test image goes from 1.44 GB to 941 MB (`du -sx /`: 1041 to 701 MB);
  what is left is Python, the dependencies and uv's cache for the wheel
  tests.

The version went to 0.3.0. The CLI flags, the `--json` events and their
stages are unchanged. dojo-portal's image can drop `inkscape fontconfig
fonts-noto-cjk fonts-noto-cjk-extra` once it takes this wheel.

## 2026-10-29 – A4 as well as A3

The certificates print on A4 as well as on A3, landscape either way, still
on plain white paper. This overrides ‘Plain white paper only’ where it says
the certificates print on ‘plain white A3 and nothing else’, and the
`<award>-<variant>.<ext>` names the earlier entries use; those entries are
left as they were written.

- **A4 is the A3 layout scaled by 1/√2**, on a 297 × 210 mm sheet: the
  columns, the crest, the margins and the text, all proportionally smaller.
  There is no A4 layout of its own and no minimum text size. A4 is not
  exactly A3 over √2 (297/420 is 0.707143, 210/297 is 0.707071), so the
  scaled layout is 0.02 mm short of the sheet's width and 0.01 mm over its
  height, at the bottom, inside the margins where nothing prints. The SVG's
  root is the A4 sheet, and the layout sits inside
  `<g transform="scale(0.7071067812)">`. An A3 sheet has no wrapper, so A3
  output is byte for byte what it was, apart from its name.
- **`--paper a3|a4` and `[paper] size`.** The key is the dōjō's default and
  the flag overrides it for one run; A3 is the default when neither says.
  The key sits in the existing `[paper]` table because a top-level
  `paper = "a4"` would clash with that table. Both are case-insensitive
  (`A4`), and the names say `a4`. A bad `--paper` is argparse's own error;
  a bad `size` names the file, `[paper] size` and both values, and is
  reported even when `--paper` is given. `config.save()` writes the key,
  and the example sets `size = "a3"`.
- **The margins scale.** `border` and `safe_inset` are millimetres of the
  A3 layout; on A4, 22 mm becomes 15.6 mm and 38 mm becomes 26.9 mm.
  Keeping them physical would put the 38 mm safe inset over the A4 text.
  `text_drop` is a fraction of the page and scales anyway.
- **Every output name carries the size**:
  `<award>-<variant>-<size>[-<suffix>].<ext>`, as in
  `dan-overlay-a3-sample.pdf` or `dan-overlay-a4-2-ヤン-ヤンセン.pdf`, and an
  inked SVG's side raster is `dan-overlay-a4-sample-textlayer.png`. The size
  goes after the variant and before the suffix: the award, the variant and
  the size are fixed vocabularies and the suffix is free text, so a reader
  splits the fixed part from the free one where it did before, and a
  listing sorts by award, variant, then size. `--suffix a4` on A3 is
  allowed (`dan-overlay-a3-a4.pdf`); the size comes first, so it is not
  ambiguous. The regression goldens keep their names from 823af58 and are
  compared through a mapping that inserts `-a3`, so they still prove the
  A3 bytes unchanged.
- **`--dpi` is per inch of the sheet.** An A4 PNG at 300 dpi is
  3508 × 2480 px; the range is 1 to 2400 at either size.
- **The ink keeps its physical grain.** The text layer is rendered at
  600 dpi of the A4 sheet, so its raster is the A3's scaled by 1/√2, and
  `ink.py` is unchanged: the grain and the blur stay the same size in mm
  while the glyphs shrink. Inside the strokes the A4 brush lifts in about a
  quarter fewer pixels (a share of 0.0227 against 0.0296; 5th percentile
  237 against 233, mean 251.7 against 251.4), a hair darker at the tips and
  indistinguishable at screen size. Grading A4 as the A3 (`ink_layer` at
  600/√2 dpi, the field scaling with the glyphs) came closer, 0.0266, but
  at the A3's cost: the ink pass takes +194 MB and 1.6 s on the Mac against
  +119 MB and 0.8 s.
- **Nothing else changes.** The other flags, the `--json` events, their
  fields and the progress stages are as they were; only the paths carry the
  size. dojo-portal reads the `file` events' paths, so it should not
  notice. The version went to 0.4.0.

Measured in `menkyo-test` on the Mac's native `linux/arm64` Docker, cgroup
`memory.peak` and wall time, median of 3, with the C-1p and C-4p runs of
`tests/acceptance/render_without_inkscape/measure.sh` plus `--paper`, in two
rounds:

| case | A3 | A4 |
|---|---|---|
| C-1p, overlay, PDF (the portal's run) | 188 MB, 2.40 s; 187 MB, 2.35 s | 142 MB, 1.45 s; 142 MB, 1.45 s |
| C-4p, overlay-flat, PDF | 57 MB, 0.21 s; 58 MB, 0.25 s | 57 MB, 0.22 s; 57 MB, 0.22 s |

- The `menkyo` process's own peak on the Mac (`peak_driver.py`, the
  portal's run): 304 MB at A3, 215 MB at A4 (71 %).
- A flat run costs the same at either size: its floor is the imports and
  the fonts, and the difference in wall time is noise.

## 2026-10-29 – Kyū grades, on a simpler sheet

A new award, `kyu`, certifies the kyū grades, the numbered grades below
shodan (first dan): from 10 kyū for a beginner up to 1 kyū. The example names
it 級位認定証 (kyū grade
certificate) with the formula 右認定ス (the above is hereby recognised); a
`dojo.toml` sets its own, as for any award. This overrides ‘Purple menkyo,
and a precept column’ where it puts the precept on every document, and
‘Printing the three hand slots’ where anything unrecognised passes through
`--rank`; both entries are left as they were written.

- **A simpler sheet, not the dan sheet.** It keeps the heading, the
  recipient, the grade, the formula, the date, the art, the dōjō and the
  signatory's office and name, with the inked look in all three variants. It
  drops the precept column and the crest (mon) with its rings and lettering,
  so that the kyū sheet looks distinct from the dan and shihan awards. For
  now its layout is what sets it apart; a calligraphy of its own is to
  follow as a separate item (see Open).
- **Two per-award keys, `crest` and `motto`**, both `true` unless set, so
  every existing award and `dojo.toml` is unchanged. Two keys rather than
  one switch, and not tied to the kyū unit: a dōjō may want a kyū sheet
  with its crest, or a licence without one. Strict booleans: `"no"` or `0`
  is an error naming the file, the award and the key.
- **Without the precept the sheet is centred.** On an award with
  `motto = false`, every column and the seal move 10 mm left
  (`NO_MOTTO_SHIFT`), so the printed block has 68.75 mm clear on the left
  and 69 mm on the right; left where they were, it sat 10 mm right of
  centre (79 against 59 mm). The crest, where there is one, stays at the
  page's centre, and the crest's place on a kyū sheet is a band of white at
  the top, as on a plain 賞状. The move hangs off the award's key, never off
  an empty `[motto] text`, so a dōjō without a precept keeps its layout and
  every regression golden is unchanged.
- **The award declares its unit in `grade_column`**: `true` (or `"dan"`) and
  `false` as before, or `"kyu"`. Case-insensitive; anything else, `1` and
  `"yes"` included (silently true until now), is an error naming the file,
  the award, the key and the values. A separate `unit` key would have let
  `grade_column = false, unit = "kyu"` exist, which means nothing. An
  explicit `--rank` on a licence still counts in dan. `config.save()` writes
  `"kyu"` only for a kyū award and `crest`/`motto` only when `false`, so a
  configuration without a kyū award saves as it did.
- **The kyū forms.** `1` to `10`; the romaji `ikkyu` … `gokyu` … `jukkyu`
  (also `shichikyu`, `hakkyu`, `jikkyu`); the belts `white` 六級, `yellow`
  五級, `orange` 四級, `green` 三級, `blue` 二級, `brown` 一級; and the
  children's steps between two belts, written with 準 (associate):
  `white-yellow` or `jun5` 準五級, `yellow-orange` or `jun4` 準四級,
  `orange-green` or `jun3` 準三級. 準 exists for those three steps and
  nowhere else, so `jun6` is a mistake, not a grade. Any case; ū and uu read
  as u, on a dan award too (`jūdan` 十段). `--rank` is normalised to NFC
  before that folding, so a macron typed as u plus a combining mark, as some
  macOS text produces, reads the same. Full-width digits are numbers here
  as on a dan award: ５ is 五級, and ０ and １１ are refused. Kanji pass
  through as given. The
  belt is an input form only and is printed nowhere. Belt names are English
  only; the portal maps its own.
- **The other unit's forms are refused.** On a kyū award, ASCII that is
  none of the above (`purple`, `11`, `5kyu`, `nidan`) is an error listing
  the forms; on a dan award, a kyū form (`yellow`, `jun5`, `gokyu`) is an
  error naming the award, where it used to print in Latin letters. Other
  ASCII on a dan award still passes through (`Shihan`). Whole words only:
  `kyudan` is still 九段. Checked for the whole run before anything is
  listed, emptied or written, so `-a dan,kyu -r yellow` writes nothing.
- **Each award reads the value in its own unit**: `-a dan,kyu -r 3` prints
  三段 and 三級. The `[sample] rank` likewise, so the example's `5` is 五級 on
  the kyū sheet; a sample that is not a grade in an award's unit is an error
  naming `[sample] rank`. A licence does not draw the sample, so it does not
  read it either.
- **A long grade shrinks.** The grade column is spaced for two characters
  at 30 mm; 準五級 would run 30 mm into the name's zone. On every award, a
  grade of n characters is set at `min(30, 60 / n)` mm from the same top,
  so 準五級 is 20 mm and `-r Shihan` 10 mm. No golden has a longer grade.
- **The file name carries `--rank` as typed** (`kyu-overlay-a3-yellow.pdf`),
  as for dan. The example's default run writes four certificates; the
  goldens run on a copy of it without `kyu`.
- **What a kyū-only run does not draw is not checked**: neither
  `[dojo] crest_ring` nor `[motto] text` nor the art on the ring.
- No new flag, `--json` event, field or progress stage. The version went to
  0.5.0: a new award in the example and a former literal now refused.

## 2026-10-30 – Kyū grades in horizontal lines, on portrait paper

The kyū certificate is now a sheet of its own: A4 portrait, 210 × 297 mm,
read in horizontal lines (yokogaki), set in Noto Serif JP SemiBold with the
dōjō's crest as a light watermark behind the text. The user chose it from
mock-ups on 30 October 2026. It replaces the vertical simpler sheet of
‘Kyū grades, on a simpler sheet’, which is removed rather than kept as an
option, and with it that entry's `motto` key and its 10 mm shift. It
overrides three entries in part: ‘A4 as well as A3’ where `[paper] size`
chooses the sheet of every award; ‘Rendered without Inkscape’ where
`document()` is the one description of the sheet; ‘Calligraphic typeface’
where every printed character is Yuji Boku. Those entries are left as they
were written. The version went to 0.6.0: the example's kyū certificate
looks entirely different and is named `a4`.

- **The unit decides the sheet.** An award with `grade_column = "kyu"`
  always gets the horizontal sheet; a dan award or a licence always the
  vertical one. There is no `layout` key: the user did not want two kyū
  sheets to maintain, nor backwards compatibility with 0.5.0's. A `layout`
  line is an unknown key and ignored, as `colour` is.
- **Top to bottom:** the heading 級位認定証, letter-spaced (16 mm, a glyph
  every 24 mm); the recipient with 殿 (11 and 9 mm), centred; the grade
  (22 mm, every 28 mm), the largest line; the body; the date, indented a
  character from the body; then the art, the dōjō and the office with the
  name, flush left at 96 mm, right of centre. The line centres are as
  mocked: heading 58 mm, name 104, grade 140, body 180 and 193, date 213,
  issuer 236, 249 and 264. Every character in #111111, in Noto Serif JP,
  never inked: nothing on it is rotated or shifted as in a vertical column,
  and `[paper] text_drop` does not move it.
- **`body` instead of the formula.** One string per printed line, one to
  three lines, printed as given; Japanese has no spaces to break a line at,
  so the dōjō breaks it. Without the key, the approved two lines,
  上記の者は本会所定の審査に合格したので and ここに認定します (本会, ‘this
  association’). The lines are flush left in a block centred on the sheet
  and on y 186.5 mm; a line too long for the width sets the whole block
  smaller. `formula` is optional on a kyū award and ignored there; still
  required on any other award.
- **The watermark.** The crest through the same `crest()`, 120 mm across,
  centred at 105, 168 mm, drawn first so that the text prints over it, its
  rings, mon and ring lettering in one grey, `round(255 × (1 − w))` for
  `watermark = w`: 0.08, 8 % of black, is #ebebeb. Per award, 0 < w ≤ 1, a
  bool refused. A light grey is a print risk on a home printer (too faint,
  banding), so the README asks for a test print. `crest = false` keeps its
  meaning on every award: no crest on a vertical sheet, no watermark on the
  kyū sheet.
- **`motto` is removed.** It existed only for the vertical kyū sheet. Since
  0.5.0's `motto = false` moved every column 10 mm, ignoring it would move a
  dōjō's columns back without a word, so it is an error on any award, naming
  the file, the award and the key and saying to delete the line.
  `NO_MOTTO_SHIFT` is gone; a dan award without a precept leaves the column
  empty, as before 0.5.0, and the regression goldens are unchanged. The kyū
  sheet never prints the precept.
- **Paper (overriding ‘A4 as well as A3’).** The kyū sheet is A4 portrait
  whatever `[paper] size` says, since that key is chosen for the landscape
  certificates. An explicit `--paper` applies to every award: `--paper a3`
  gives A3 portrait, 297 × 420 mm, the A4 layout scaled by √2 in one
  wrapper, the mechanism the landscape A4 uses. Names carry the real size,
  `kyu-overlay-a4-sample.pdf` beside `dan-overlay-a3-sample.pdf`. `PAPERS`
  and `SCALE` stay the landscape tables; a portrait pair sits beside them.
- **Variants.** All three stay, so `--all` and the portal's
  `--variants=overlay-flat` keep working: `overlay` and `overlay-flat` are
  the same drawing, byte for byte, and `--no-ink` changes nothing. `proof`
  adds the border and safe inset (`border` and `safe_inset` scaled by 1/√2,
  as for the landscape A4), the zones for a blank name and grade, nine date
  slots, and a seal circle right of the signatory's name, on the proof only.
  Room for it, 20 mm, is kept on every variant, so the proof's text is the
  overlay's. The circle has a stamp's radius, 9 mm. Centred on the
  signatory's line (264 mm), it would cross the safe inset, so its centre
  rises until the circle's bottom sits on the inset: 261.1 mm by default.
- **Long lines.** The grade is never shrunk: 準五級 is set at 五級's size.
  A long name shrinks to the safe width, still centred. A heading of seven or
  more characters closes its spacing up before it shrinks. An issuer line
  too long for the room left of the seal moves the block left; only when
  that would bring the block's centre within 5 mm of the page's does it
  shrink.
- **The glyph check follows the face.** Everything the kyū sheet prints,
  its heading and body included, is checked against Noto Serif JP: 𠮷 prints
  on it and is refused on the dan sheet; 한 is refused on both. Not drawn,
  not checked: the precept and the formula on a kyū-only run, and the ring
  when `crest = false`.
- **Progress.** No new flag, `--json` event, field or stage; a kyū sheet has
  no `text` or `ink` step, so the example's default run is 10 steps where it
  was 12.
- **Closes the Open item** ‘A second brush font for the simpler sheet’: the
  kyū sheet now differs in its face (a mincho, not Yuji Boku) as well as its
  layout.

## Open

- **Confirm the katakana transcription of any recipient's name** with the
  recipient before printing.
- **An annotated version in Dutch (asked 28 October 2026).** Besides the inked
  overlay, a default run should also produce a version that explains what
  the certificate says, in Dutch, for that recipient. The English
  `docs/*-explained.md` pages are the starting point for the content.
  Decided so far: a **companion A4 sheet** (a small image of the certificate
  with numbered columns; per column the Japanese, its reading and its meaning
  in Dutch; the recipient's own name, grade and date read out), and the
  dōjō's own parts (art, dōjō, signatory, motto, crest) explained from
  **optional Dutch text in `dojo.toml`**, falling back to a generic
  description of the form. It joins the default run once built.
- **A smaller footprint: memory and container size (asked 29 October 2026).**
  See whether both can come down further, now that Inkscape is gone.
  Starting points from 0.3.0:
  - Memory: a C-1 run peaks at 189 MB, most of it the ink pass; a flat run
    at 64 MB, of which about 25 MB is imports.
  - Container size: numpy, scipy and Pillow are most of an installed image
    (about 234 MB in the spike), and scipy is used only by `ink.py`. The
    test image is 941 MB, much of it uv's wheel cache.
  Measure the portal's image as well, since that is what runs on the NAS.
