"""house-style-sweep: README.md, DECISIONS.md, tests/README.md, NOTICE and
docs/*.md restyled to the house style, facts untouched, and the Open item
closed.

Contract: docs/work/house-style-sweep/acceptance.md.  The lint itself and
the history comparison live in house_style.py, beside this file, so the
older items' history tests use the same rules (AC-14).  AC-7, AC-8, AC-9,
AC-12's second half, AC-15 and AC-17 are checked at validation, partly with
house_style_sweep/check_sweep.py: they compare against the commit before
the sweep, which later items move on from.

The lint runs on every later change too: new text follows the house style.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import support

sys.path.insert(0, str(Path(__file__).resolve().parent))
import house_style as hs  # noqa: E402

BEFORE = "3f025b9"          # HEAD when the item was planned
FILES = hs.in_scope_files()
IDS = [hs.rel(p) for p in FILES]


def _git(*args):
    if not shutil.which("git") or not (support.REPO / ".git").exists():
        return None             # the Docker image has neither
    r = subprocess.run(["git", "-C", str(support.REPO), *args], capture_output=True, text=True)
    return r if r.returncode == 0 else None


def _old(rel):
    if not (support.REPO / ".git").exists():
        pytest.skip("no git history here (the Docker image)")
    r = _git("show", f"{BEFORE}:{rel}")
    if r is None:
        pytest.skip(f"{BEFORE} not available (a shallow clone)")
    return r.stdout


def _decisions():
    return (support.REPO / "DECISIONS.md").read_text(encoding="utf-8")


def test_scope():
    """The four named files and whatever docs/*.md holds (the glob is the
    scope; docs/work/ is not in it)."""
    assert IDS[:4] == ["README.md", "DECISIONS.md", "tests/README.md", "NOTICE"]
    assert "docs/README.md" in IDS[4:]
    assert all(re.fullmatch(r"docs/[^/]+\.md", i) for i in IDS[4:]), IDS


# -------------------------------------------------------------------- AC-1 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac1_no_em_dash(path):
    hits = hs.em_dashes(path)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac1_code_keeps_its_dashes():
    """Code is not prose: the README's TOML example keeps its comments as
    they were, em dashes included (AC-9 holds every code block byte for
    byte; this is the case most likely to be swept by accident)."""
    readme = (support.REPO / "README.md").read_text(encoding="utf-8")
    block = readme.split("```toml\n", 1)[1].split("```", 1)[0]
    assert '# mm, the margin kept clear all round — see "Printing"' in block
    assert '# fraction of page height — see "Where the columns start"' in block


# -------------------------------------------------------------------- AC-2 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac2_quotation_marks(path):
    hits = hs.straight_quotes(path) + hs.nested_quotes(path)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac2_lint_cases(tmp_path):
    doc = tmp_path / "x.md"
    ok = ("The *dono*'s register, the dōjō's crest, ‘a “nested” quote’, and code:\n"
          "`say \"hi\"` and a span over a line break, `[art]\nname = \"x\"`.\n")
    doc.write_text(ok, encoding="utf-8")
    assert hs.straight_quotes(doc) + hs.nested_quotes(doc) == []
    for bad in ('A "quote".\n', "An 'opening quote'.\n", "Emphasis *'quoted'*.\n",
                "A “bare double”.\n"):
        doc.write_text(bad, encoding="utf-8")
        assert hs.straight_quotes(doc) + hs.nested_quotes(doc), bad


# -------------------------------------------------------------------- AC-3 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac3_headings_in_sentence_case(path):
    hits = hs.heading_case(path)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac3_lint_catches_title_case(tmp_path):
    """The heading check is not vacuous."""
    doc = tmp_path / "x.md"
    doc.write_text("# 段位免状 – Dan Rank Certificate\n\n## Yuji Boku and the PDF\n",
                   encoding="utf-8")
    hits = hs.heading_case(doc)
    assert len(hits) == 1 and "'Rank'" in hits[0], hits
    assert "house_style.PROPER" in hits[0]


# -------------------------------------------------------------------- AC-4 ---
# The serial commas found when the item was planned (house_style.py's
# heuristic, read by hand).  Each must be gone; the heuristic's other
# candidates are reviewed at validation, since most are commas between
# clauses, which stay.
KNOWN_SERIAL_COMMAS = {
    "README.md": ["checked against Japanese practice, and are printed",
                  "bump it, commit, and build"],
    "DECISIONS.md": ["its teachers, or the certificate",
                     "peacock eye-feathers, and a chain",
                     "outside the checkout, renders, and checks"],
    "tests/README.md": ["the set of files written, and the"],
}


@pytest.mark.parametrize("rel", sorted(KNOWN_SERIAL_COMMAS))
def test_ac4_known_serial_commas_gone(rel):
    joined = " ".join(t for _, t in hs.paragraphs(support.REPO / rel))
    joined = re.sub(r"\s+", " ", joined)
    left = [s for s in KNOWN_SERIAL_COMMAS[rel] if s in joined]
    assert left == [], left


# -------------------------------------------------------------------- AC-5 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac5_dates(path):
    hits = hs.iso_dates_in_prose(path)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac5_headings_keep_iso_dates():
    heads = [h for h in re.findall(r"^## .*$", _decisions(), re.M) if h != "## Open"]
    bad = [h for h in heads if not re.match(r"## \d{4}-\d{2}-\d{2} – \S", h)]
    assert bad == [], bad


# -------------------------------------------------------------------- AC-6 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac6_british_spelling(path):
    hits = hs.american_spellings(path)
    assert hits == [], "\n" + "\n".join(hits)


def test_ac6_lint_cases(tmp_path):
    doc = tmp_path / "x.md"
    doc.write_text("Resizing, maize, an honorary title, the honorarium, the honorific,\n"
                   "greyscale, practice and a licence; argparse's ‘unrecognized arguments’.\n",
                   encoding="utf-8")
    assert hs.american_spellings(doc) == []
    for bad in ("normalized", "color", "grayscale", "practiced", "toward", "honor", "center"):
        doc.write_text(f"The {bad} here.\n", encoding="utf-8")
        assert hs.american_spellings(doc), bad


# ------------------------------------------------------------------- AC-10 ---
def test_ac10_decisions_history_keeps_its_facts():
    """Every entry up to the sweep keeps its facts through the full restyle
    the user chose (Q-1): numbers, dates, code spans, links, the titles and
    program output it quotes, its dated heading and its place.  Meaning is
    read by hand (M-2)."""
    problems = hs.history_problems(_old("DECISIONS.md"), _decisions(), baseline=BEFORE)
    assert problems == [], "\n" + "\n".join(problems)


OLD_LOG = """# Log

Why. One entry per decision.

## 2026-09-05 — Brief

- **A3 at the mon**, 420 × 297 mm — the mon is large, "plain", red, green,
  and blue, `a
  b` stays. See [spike](docs/x.md).
- **Date: 西暦.** It is genuinely important to note that era years go stale.

## 2026-09-06 — Later

Overrides "A3 at the mon" of "Brief"; argparse says "unknown variant".

## Open
"""
# A full restyle (Q-1): dashes, quotes, serial comma, case, a gloss, a code
# span rewrapped, a hollow sentence rewritten, words cut.
RESTYLED = """# Log

Why: one entry per decision.

## 2026-09-05 – brief

- **A3 at the mon**, 420 × 297 mm: the mon (family crest) is big,
  ‘plain’, red, green and blue; `a b` stays. See [spike](docs/x.md).
- **Date: 西暦.** 西暦, the Western calendar: era years go stale.

## 2026-09-06 – Later

Overrides ‘A3 at the mon’ of ‘Brief’; argparse says ‘unknown variant’.

## Open
"""


def test_ac10_comparison_accepts_a_full_restyle():
    assert hs.history_problems(OLD_LOG, RESTYLED) == []


@pytest.mark.parametrize("change", [
    ("420", "421"),                                     # a number
    ("420 × 297 mm", "A3"),                             # a number dropped
    ("`a b`", "`a c`"),                                 # a code span
    ("`a b` stays", "it stays"),                        # a code span dropped
    ("[spike](docs/x.md)", "[spike](docs/y.md)"),       # a link
    ("**A3 at the mon**", "**A3 sheet at the mon**"),   # a bold title the log quotes
    ("‘A3 at the mon’", "‘the A3 sheet’"),              # a quotation of a title
    ("‘unknown variant’", "‘unknown option’"),          # quoted program output
    ("## 2026-09-06 – Later", "## 2026-09-07 – Later"),  # a dated heading
    ("## 2026-09-06 – Later", "## 2026-09-06 – Afterwards"),
    ("era years go stale.", "era years go stale.\n- **Kyū too.** A new decision."),
    ("era years go stale.", "era years go stale. " + "More words here. " * 12),
    ("the mon (family crest) is big", "the mon is big on 1 sheet"),  # a number added
], ids=lambda c: c[1][:28])
def test_ac10_comparison_is_not_vacuous(change):
    changed = RESTYLED.replace(*change)
    assert changed != RESTYLED, change
    assert hs.history_problems(OLD_LOG, changed), change


def test_ac10_an_entry_dropped_or_reordered_fails():
    blocks = hs.decisions_blocks(RESTYLED)
    dropped = blocks[0] + blocks[1] + "## Open\n"
    swapped = blocks[0] + blocks[2] + blocks[1] + "## Open\n"
    assert hs.history_problems(OLD_LOG, dropped)
    assert hs.history_problems(OLD_LOG, swapped)


def test_ac10_kanji_are_facts():
    """Swapping or dropping kanji fails; a gloss may add some."""
    old = "# Log\n\n## 2026-09-05 — A\n\n- **1 → 初段, never 一段**, 西暦 dates.\n\n## Open\n"
    assert hs.history_problems(old, old.replace(" — ", " – ")) == []
    assert hs.history_problems(old, old.replace("西暦 dates", "西暦 (Western) dates, not 和暦"))\
        == []
    for change in (("初段, never 一段", "一段, never 初段"), ("西暦", "和暦"), ("西暦 ", "")):
        assert hs.history_problems(old, old.replace(*change)), change
    # the out-of-order branch reports, never raises (review R-9)
    assert hs.cjk_lost(["A", "B"], ["B", "A"]) == ["B (out of order)"]
    assert hs.cjk_lost(["A", "B", "C"], ["A", "C", "B"]) == ["C (out of order)"]
    assert hs.cjk_lost(["A", "B"], ["A", "x", "B", "y"]) == []
    assert hs.cjk_lost(["A"], []) == ["A"]
    # and in the other files (AC-9)
    a = hs.facts("Writes 段位免状 and 右授与ス, 西暦二〇二六年九月五日.\n")
    b = hs.facts("Writes 段位免状 and 右授与ス, 西暦二〇二六年九月六日.\n")
    assert hs.cjk_lost(a["cjk"], b["cjk"]) == ["西暦二〇二六年九月五日"]
    assert hs.cjk_lost(a["cjk"], hs.facts("段位免状, 右授与ス (弐), 西暦二〇二六年九月五日\n")["cjk"]) == []


def test_ac10_history_edits_follow_the_baseline():
    """An after-the-fact edit is set aside only against a baseline from
    before it: against 3f025b9 the reworded bullets are compared like the
    rest (review R-1)."""
    if _git("rev-parse", "8509b85") is None or _git("rev-parse", BEFORE) is None:
        pytest.skip("no git history here (the Docker image)")
    assert [e[0] for e in hs.edits_before(BEFORE)] == []
    assert [e[0] for e in hs.edits_before("8509b85")] == []
    assert [e[0] for e in hs.edits_before("823af58")] == ["remove-super" "sample"]
    assert [e[0] for e in hs.edits_before(None)] == ["remove-super" "sample"]
    text = _decisions()
    pattern = hs.HISTORY_EDITS[0][2]
    m = pattern.search(text)
    assert m, "the reworded bullets are not found"
    region = m.group(0)
    number = re.search(r"\d+", re.sub(r"`[^`]*`", " ", region))
    assert number, region
    changed = text[:m.start()] + region.replace(number.group(0), number.group(0) + "1", 1) \
        + text[m.end():]
    assert hs.history_problems(_old("DECISIONS.md"), changed, baseline=BEFORE)


def test_ac14_history_edits_registry():
    """One registry of allowed after-the-fact history edits, applied by every
    comparison; the older tests no longer carry their own."""
    assert [(slug, commit) for slug, commit, _ in hs.HISTORY_EDITS] == \
        [("remove-super" "sample", "8509b85")]
    for name in ("test_ac_cli_only.py", "test_ac_plain_white.py",
                 "test_ac_render_without_inkscape.py"):
        text = (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
        assert "house_style.history_problems(" in text, name
        assert "_without_reworded_bullets" not in text, name


# ------------------------------------------------------------------- AC-11 ---
PINNED_BLOCKS = hs.PINNED_BLOCKS


def test_ac11_history_pinned():
    """After the sweep, the history is held byte for byte (works without
    git, so in the Docker image too)."""
    pins = hs.pinned_hashes()
    assert pins is not None, f"{hs.rel(hs.PIN_FILE)} missing: the tester pins it at validation"
    assert len(pins) == PINNED_BLOCKS, len(pins)
    blocks = hs.decisions_blocks(_decisions())
    assert len(blocks) >= PINNED_BLOCKS
    changed = [f"block {i}: {blocks[i].splitlines()[0]!r}"
               for i, h in enumerate(pins) if hs.entry_hash(blocks[i]) != h]
    assert changed == [], "history changed since the sweep:\n" + "\n".join(changed)


# ------------------------------------------------------------------- AC-12 ---
def test_ac12_open_item_closed():
    _, open_ = _decisions().split("\n## Open\n", 1)
    items = re.findall(r"^- \*\*(.+?)\*\*", open_, re.M)
    assert items, "the Open list is empty"
    assert not [i for i in items if re.search(r"house.style", i, re.I)], items
    # other tests find these by how they start (AC-13); no gloss in a title
    # (paper-format closed "Paper format", its AC-21)
    for start in ("Kyū grades", "An annotated version in Dutch"):
        assert [i for i in items if i.startswith(start)], (start, items)


# ------------------------------------------------------------------- AC-13 ---
README_SUBSECTIONS = ["Where the columns start"]     # the README's TOML comment points here
README_SECTIONS = ["Quick start", "As a package", "Configuring it for your dōjō",
                   "Options", "Variants", "Filling the document in", "Printing",
                   "How it looks the way it does", "Layout", "Writing for the recipient",
                   "Licence"]


def test_ac13_readme_sections_kept():
    """Other items' tests find README sections by their exact heading."""
    heads = re.findall(r"^## (.*)$", (support.REPO / "README.md").read_text(encoding="utf-8"),
                       re.M)
    missing = [h for h in README_SECTIONS if h not in heads]
    assert missing == [], (missing, heads)
    subs = re.findall(r"^### (.*)$", (support.REPO / "README.md").read_text(encoding="utf-8"),
                      re.M)
    assert [h for h in README_SUBSECTIONS if h not in subs] == [], subs


def test_ac13_quoted_program_output_kept():
    """Words a program prints keep the program's spelling inside the new
    quotation marks (argparse is American)."""
    text = _decisions()
    assert "‘unrecognized arguments’" in text
    assert "‘unknown variant’" in text


def test_ac13_decisions_headings_other_tests_find():
    heads = [hs.entry_heading_key(h + "\n") for h in re.findall(r"^## .*$", _decisions(), re.M)]
    for title in ("2026-09-05 – Printing the three hand slots",
                  "2026-09-05 – Output, and the super" "sampling cap",
                  "2026-09-05 – Purple menkyo, and a precept column",
                  "2026-10-28 – The command is the product",
                  "2026-10-28 – Plain white paper only",
                  "2026-10-29 – The ink pass grades the alpha alone",
                  "2026-10-29 – Rendered without Inkscape"):
        assert [h for h in heads if h.startswith("## " + title)], title


def test_ac13_titles_quoted_by_the_renderer_entry():
    """test_ac35_decisions_entry finds these, quoted, in the entry that
    overrides them; the bold titles they quote are unchanged too."""
    blocks = hs.decisions_entries(_decisions())
    body = next(b for b in blocks if "Rendered without Inkscape" in b.splitlines()[0])
    titles = ("The font is vendored", "Output, and the super" "sampling cap",
              "Installed-copy behaviour", "Packaging is tested by rendering")
    for t in titles:
        assert t in body, t
    text = _decisions()
    for bold in ("**The font is vendored, not installed.**",
                 "**Installed-copy behaviour is kept.**",
                 "**Packaging is tested by rendering.**"):
        assert bold in text, bold


# ------------------------------------------------------------------- AC-16 ---
@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_ac16_markup_intact(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert sum(1 for l in lines if hs._FENCE.match(l)) % 2 == 0, "unbalanced code fence"
    # every table keeps one cell count from its header to its last row
    table, bad = [], []
    for n, l in enumerate(lines + [""], 1):
        if l.lstrip().startswith("|"):
            table.append((n, l.count("|") - l.count("\\|")))
            continue
        if table and len({c for _, c in table}) > 1:
            bad.append(table[0][0])
        table = []
    assert bad == [], f"tables with ragged rows at lines {bad}"
    # inline code spans are closed within their paragraph
    para, start, fence = [], 1, False
    for n, l in enumerate(lines + [""], 1):
        if hs._FENCE.match(l):
            fence = not fence
            continue
        if fence:
            continue
        if l.strip():
            para.append(l)
            continue
        assert "".join(para).count("`") % 2 == 0, f"line {start}: unpaired backtick"
        para, start = [], n + 1
    # relative links and images point at files that exist
    for target in re.findall(r"\]\(([^)#\s]+)[^)]*\)|src=\"([^\"]+)\"", text):
        t = next(x for x in target if x)
        if re.match(r"[a-z]+:", t):
            continue
        assert (path.parent / t).exists(), f"broken link {t}"


def test_ac7_first_mentions_case_insensitive(tmp_path):
    doc = tmp_path / "x.md"
    doc.write_text("Kyū grades come first. Dōjō life.\n\nJūjutsu and Ryū; 殿 too.\n",
                   encoding="utf-8")
    seen = hs.first_mentions(doc)
    for term in ("kyū", "dōjō", "jūjutsu", "ryū", "殿"):
        assert term in seen, (term, seen)


def test_lint_reads_a_code_span_over_a_line_break(tmp_path):
    doc = tmp_path / "x.md"
    doc.write_text('Checked: a `[sample]` grade, `[art]\nname = "x — y"` against both.\n',
                   encoding="utf-8")
    assert hs.em_dashes(doc) == [] and hs.straight_quotes(doc) == []


def test_ac16_readme_note_and_image():
    readme = (support.REPO / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# menkyo-menjo-builder ")
    assert "> [!NOTE]\n" in readme
    assert '<img src="docs/three_up.png"' in readme
