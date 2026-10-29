# paper-format: review

## Round 1

Verdict: APPROVE.

**Checks run:**
- `uv run pytest`: 730 passed.
- A3 is byte for byte the same as `bc92fbe` in all 20 compared files, once
  names are mapped (the inked SVG differs only in its `xlink:href`).
- A4 geometry is correct: the root viewBox, one scale group, the `<image>`
  outside it in sheet mm, the text-layer bbox in sheet mm, and guides,
  `text_drop`, traced glyphs, `safe_inset` and `border` all scaling.
- A bad config size is caught in `config.load()`, so `--list` and
  `--paper` still report it.
- DECISIONS gains one new entry and loses the Open item; no existing entry
  changed.

**[R-1] minor, docs.** `CLAUDE.md:3` still says ‘A3 landscape’. *Owner:*
orchestrator.

**[R-2] minor, record.** `build_diploma.py:59-62` and the new DECISIONS
entry give only ‘0.02 mm short of the width’. The layout is also 0.01 mm
over the height, at the bottom, inside the margins. *Owner:* developer
(code comment), docs (DECISIONS).

**[R-3] nit.** The default size is spelled twice: `DEFAULT_PAPER` in
`build_diploma.py:66` and `Config.paper_size` in `config.py:65`. Derive
both from one place. *Owner:* developer.

**[R-4] nit, UX.** The `--paper` help reads ‘(default: a3, from [paper]
size in the configuration, or a3 when it has none)’. Tidy it. *Owner:*
developer.

**[R-5] nit, docs.** The `VARIANTS` comment at `build_diploma.py:628`
still says ‘12 mm columns’. Write ‘the columns’, as the README does.
*Owner:* developer.
