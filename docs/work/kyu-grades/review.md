# kyu-grades: review

## Round 1

Verdict: APPROVE. No blocker or major finding.

**Checks run:**
- `uv run pytest`: 990 passed.
- `scripts/test-docker.sh`: 984 passed, 6 skipped (no git history in the
  image).
- Output compared with HEAD's `src/`: byte-identical across default,
  named, blank, licence, A4, literal 弐段, `juudan` and empty-motto runs.
  Only `-r Shihan` differs: it now shrinks, as OQ-12 intends.
- Installed 0.5.0 wheel: `--list` gives the four awards; the portal form
  with `--rank=white-yellow` prints 準; a mixed-unit `--json` run gives one
  `error`. The kyū proof is centred and 準五級 stays clear of the name zone.
- Rank parsing: about 30 edge inputs per unit. Personal-data rules hold.

**[R-1] minor, correctness.** At `config.py:201` and `:209`, `json.dumps`
of a TOML date in `grade_column`, `crest` or `motto` raises `TypeError`
inside the error path. The run then ends in a traceback, and the `--json`
event names neither file, award nor key. `[paper] size` at `:175` has the
same flaw. Use `default=str` or a helper. *Owner:* developer.

**[R-2] minor, correctness.** `build_diploma.py:338-341` folds only the
precomposed ū. Text in NFD (u + U+0304) stays non-ASCII, so it becomes a
literal or a missing-glyph error. Normalise to NFC before folding, and
test it. *Owner:* developer.

**[R-3] minor, record.** The new DECISIONS entry gives a reason for
dropping the crest and the precept that the user never gave. *User,
29 October 2026:* the reason is to make the kyū sheet visually distinct
from the dan and shihan awards. It is distinguished by its layout now; a
distinct calligraphy (a second brush font) follows as its own item.
*Owner:* docs.

**[R-4] nit.** `build_diploma.py:461`: `x_rank` is None when `document()`
is called directly with `rank=` and `rank_column=False`, so `vcol` crashes.
Guard it. *Owner:* developer.

**[R-5] nit, docs.**
- Ragged wraps in `docs/README.md` and the README's `crest`/`motto`
  paragraph.
- The README says a kyū sheet ‘checks neither the ring nor the precept’;
  that holds only for a run of kyū sheets only.
*Owner:* docs.

User decision, the same day: full-width digits (５) are read as numbers on
a kyū award too (５ → 五級), as on dan.
