# house-style-sweep: review

## Round 1

Verdict: CHANGES REQUESTED. The prose sweep holds up. The independent
meaning read of DECISIONS.md, entry by entry with `git diff --word-diff`,
found no entry whose meaning shifted: all 20 entries, the preamble and the
Open list keep their meaning. Every gloss is accurate and sits in the body.
AC-13 text is kept, and every CJK run is unchanged apart from the added 弐
(the 大字 gloss). Two blind spots in the facts-preserving tooling, both
confirmed by mutation, are why changes are requested.

**[R-1] major, tests.** `house_style.py:498-512, 549`: HISTORY_EDITS
regions are set aside on both sides of every comparison, whatever the
baseline. Against post-edit baselines (3f025b9, 8509b85) the region is
never compared: changing ‘32767 px’, ‘capped at 4’ or the ‘Supersampling
removed’ date passes. Give each entry the commit that made the edit, and
apply it only when the baseline predates that commit (`merge-base
--is-ancestor`). Without git, apply all of them. Add a non-vacuity case.
*Owner:* tester.

**[R-2] major, tests.** `entry_facts` and `facts()` ignore kanji and kana:
swapping 初段/一段 in DECISIONS passes, and so would a changed 段位免状 or
西暦… in the README or the recipient pages. Add the multiset of CJK runs
as a fact: every old run must survive, and additions are allowed (glosses).
Add a non-vacuity case. *Owner:* tester.

**[R-3] minor, tests.** `restyle_problems` tokenises the README with its
fenced blocks still in, so backticks pair across fences and the
‘rewording’ report becomes whole sections. Strip code blocks first.
*Owner:* tester.

**[R-4] minor, tests.** The migrated history tests' docstrings say ‘word
for word, modulo the house style’. Since Q-1 the check is
facts-preserving. *Owner:* tester.

**[R-5] minor, tests.** `pin_history.py` neither checks that layer 1
passes before writing, nor ties `--allow` to HISTORY_EDITS. *Owner:*
tester.

**[R-6] nit, docs.** `README.md:216-217` and `NOTICE:40-41`: ‘mon
(crest)… yotsume-bishi (four lozenges), a traditional kamon (family
crest)’ is dense, and ‘four lozenges’ describes the shape rather than the
name. Rephrase. *Owner:* docs.

**[R-7] nit, docs.**
- `README.md:265`: romaji is glossed ‘Latin letters’; use ‘Japanese in
  Latin letters’ as DECISIONS does.
- `docs/README.md` table: renshi is glossed but shihan is not; gloss both
  or neither.
*Owner:* docs.

**[R-8] nit, docs.** Over-long lines at `DECISIONS.md:94, 290` and
`README.md:311`. Rewrap, except lines with a code span. *Owner:* docs.

User decision, the same day: renshi is glossed ‘polished expert’ (not
‘tempered expert’).

## Round 2

Verdict: APPROVE. All of R-1 to R-8 are fixed.

**Checks run:**
- `uv run pytest`, with the pin test deselected: 630 passed.
- The reviewer's repros now fail as they should: 32767 → 32768, the
  ‘Supersampling removed’ date, capped 4/1 → 8/2, and swapping 初段 and 一段.
- Every old CJK run survives; the only addition is 弐.

**Docs and meaning:**
- The Brief's word-diff shows only dashes, the mon gloss and one serial
  comma.
- The meaning read is unchanged: same meaning in every entry.

The stricter ‘old kanji runs in order’ rule is worth keeping. Later items
cannot hit a false failure: the baselines are frozen after the pin, and
HISTORY_EDITS covers deliberate edits. What it catches, swapped kanji, is
the most consequential error these files can carry.

**[R-9] minor, tests.** `house_style.py:505-512` (`cjk_lost`) raises
IndexError when the swapped runs come last (`[A,B] → [B,A]`). The test
still goes red, but `check_sweep.py` and `pin_history.py` crash instead
of reporting. Guard the bounds, and add the case to
`test_ac10_kanji_are_facts`. *Owner:* tester.

**[R-10] nit, docs.** `README.md:265` is 90 characters after the romaji
gloss. Rewrap it. *Owner:* docs.
