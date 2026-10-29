"""House-style helpers for the docs: a lint over the prose of the in-scope
files, and the comparison of DECISIONS.md history modulo the house style.

Contract: docs/work/house-style-sweep/acceptance.md.  The house style is
Wouter's (~/dev/house-style, principles/writing.md): sentence-case headings
(WRI-001), British English (WRI-004), single quotes ‘…’ with double “…”
inside and a spaced en dash ` – `, never an em dash (WRI-005), no serial
comma (WRI-006), dates spelled out in running text and ISO in headings,
tables and file names (WRI-007).

Only prose is checked.  Fenced and indented code blocks, inline code spans,
HTML tags and link targets are left out, so an em dash or a straight quote
that a program prints, or that sits in a TOML or shell example, is never
reported.

Run it directly for a report of every finding and the serial-comma
candidates; add --terms for the first mention of each Japanese term per
file:

    uv run python tests/acceptance/house_style.py [--terms]
"""

import difflib
import hashlib
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# The files the sweep restyles and the lint keeps in style (AC-1).
# docs/work/** is the agents' paperwork and is out of scope.
def in_scope_files():
    files = [REPO / "README.md", REPO / "DECISIONS.md", REPO / "tests" / "README.md",
             REPO / "NOTICE"]
    files += sorted((REPO / "docs").glob("*.md"))
    return files


def rel(path):
    path = Path(path).resolve()
    return path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else str(path)


# --------------------------------------------------------------- the prose ---
@dataclass
class Line:
    n: int              # 1-based line number in the file
    kind: str           # "heading", "table" or "prose"
    text: str           # code spans, HTML tags and link targets blanked out
    raw: str


_FENCE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_HTML_TAG = re.compile(r"<[A-Za-z/!][^>]*>")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_AUTOLINK = re.compile(r"https?://\S+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")


_PLACEHOLDER = "⁣code⁣"


def blank_code(text, open_span=False):
    """Replace each inline code span by a placeholder that no check matches.

    A span may run over a line break (`[art]` and `name` on two lines):
    `open_span` says the line starts inside one, and the second value
    returned says whether it ends inside one."""
    if open_span:
        i = text.find("`")
        if i < 0:
            return _PLACEHOLDER, True
        text = _PLACEHOLDER + text[i + 1:]
    text = _CODE_SPAN.sub(_PLACEHOLDER, text)
    i = text.find("`")
    if i >= 0:
        return text[:i] + _PLACEHOLDER, True
    return text, False


def prose_lines(path):
    """Every line of the file that is prose, a heading or a table row, with
    inline code, HTML tags and link targets blanked out.  Fenced blocks and
    indented code blocks (four spaces after a blank line, outside a list) are
    skipped whole."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    out = []
    in_fence = False
    in_indented = False
    prev_blank = True
    in_list = False
    open_span = False
    for i, raw in enumerate(lines, 1):
        if _FENCE.match(raw):
            in_fence = not in_fence
            prev_blank, open_span = False, False
            continue
        if in_fence:
            continue
        if not raw.strip():
            prev_blank, open_span = True, False
            continue
        indented = raw.startswith("    ") or raw.startswith("\t")
        if in_indented and indented:
            continue
        in_indented = False
        if indented and prev_blank and not in_list:
            in_indented = True
            prev_blank = False
            continue
        if _LIST_ITEM.match(raw):
            in_list = True
        elif not raw.startswith(" ") and prev_blank:
            in_list = False
        prev_blank = False
        if re.match(r"^#{1,6}\s", raw):
            open_span = False
        text, open_span = blank_code(raw, open_span)
        text = _HTML_TAG.sub(" ", text)
        text = _LINK_TARGET.sub("]", text)
        text = _AUTOLINK.sub(" ", text)
        if re.match(r"^#{1,6}\s", raw):
            kind = "heading"
        elif raw.lstrip().startswith("|"):
            kind = "table"
        else:
            kind = "prose"
        out.append(Line(i, kind, text, raw))
    return out


def paragraphs(path):
    """Runs of consecutive prose lines (a list item with its continuation, or
    a plain paragraph), joined with spaces: [(first line number, text)]."""
    paras, cur, start, last = [], [], None, None
    for ln in prose_lines(path):
        if ln.kind != "prose":
            if cur:
                paras.append((start, " ".join(cur)))
            cur, start, last = [], None, ln.n
            continue
        new_item = _LIST_ITEM.match(ln.raw) or ln.raw.lstrip().startswith(">") and not cur
        if cur and (last is None or ln.n != last + 1 or new_item):
            paras.append((start, " ".join(cur)))
            cur, start = [], None
        if not cur:
            start = ln.n
        cur.append(ln.text.strip().lstrip(">").strip())
        last = ln.n
    if cur:
        paras.append((start, " ".join(cur)))
    return paras


# ------------------------------------------------------------------ checks ---
def em_dashes(path):
    """WRI-005: no em dash outside code."""
    return [f"{rel(path)}:{ln.n}: em dash: {ln.raw.strip()[:90]!r}"
            for ln in prose_lines(path) if "—" in ln.text]


# A straight ' that opens a quotation: after a space, bracket or dash, or
# after emphasis unless it is a possessive or contraction (*dono*'s).
_OPEN_SINGLE_STRAIGHT = re.compile(
    r"(?:^|[\s(\[/—–-])'(?=[^\s'])|[*_]'(?!(?:s|t|d|ll|re|ve)\b)(?=[^\s'])")


def straight_quotes(path):
    """WRI-005: quotation marks are ‘…’ and “…”, never straight.  A straight
    apostrophe inside a word (the dōjō's) is not a quotation mark and is
    left alone."""
    hits = []
    for ln in prose_lines(path):
        if '"' in ln.text:
            hits.append(f"{rel(path)}:{ln.n}: straight double quote: {ln.raw.strip()[:90]!r}")
        elif _OPEN_SINGLE_STRAIGHT.search(ln.text):
            hits.append(f"{rel(path)}:{ln.n}: straight single quote: {ln.raw.strip()[:90]!r}")
    return hits


def nested_quotes(path):
    """WRI-005: double quotes “…” only inside single ones ‘…’."""
    hits = []
    for n, text in paragraphs(path):
        depth = 0
        for i, ch in enumerate(text):
            if ch == "‘":
                depth += 1
            elif ch == "’":
                between = (i > 0 and text[i - 1].isalnum()
                           and i + 1 < len(text) and text[i + 1].isalnum())
                if not between and depth:
                    depth -= 1
            elif ch == "“" and depth == 0:
                hits.append(f"{rel(path)}:{n}: “ outside ‘…’: {text[max(0, i - 30):i + 40]!r}")
                break
    return hits


# Words that keep their capital inside a heading: proper nouns, product and
# font names, languages.  Acronyms, code, kanji and words with a digit are
# exempt by shape.
PROPER = {
    "Inkscape", "Yuji", "Boku", "Noto", "Serif", "SemiBold", "Python", "Docker",
    "Linux", "Mac", "macOS", "Japanese", "Dutch", "English", "European", "Western",
    "Gregorian", "Pillow", "NumPy", "SciPy", "GitHub", "Django",
    "Hakko", "Ryu", "Ryū", "Kinuta", "Adobe", "Open", "Font", "License", "Reiwa",
    "Cairo", "Ghost" "script", "Latin", "Debian", "Windows", "Homebrew", "Vorselaar",
    "Brief",            # DECISIONS.md's first entry, ‘the Brief’, as later ones name it
}
_SEPARATOR = re.compile(r"\s[–—]\s|:\s")


def heading_case(path):
    """WRI-001: sentence case.  The first word of the heading, and the first
    word after a dash separator or a colon, may carry a capital; after that,
    only a proper noun (PROPER) or an acronym."""
    hits = []
    for ln in prose_lines(path):
        if ln.kind != "heading":
            continue
        title = re.sub(r"^#+\s*", "", ln.text)
        for part in _SEPARATOR.split(title):
            words = re.findall(r"[^\s/()]+", part)
            first = True
            for w in words:
                core = w.strip(".,;:!?*_‘’“”'\"")
                if not core or not re.search(r"[A-Za-z]", core):
                    continue
                if first:
                    first = False
                    continue
                if (core[0].isupper() and core not in PROPER
                        and not re.search(r"\d|⁣", core)
                        and not (sum(c.isupper() for c in core) > 1)):
                    hits.append(f"{rel(path)}:{ln.n}: heading not in sentence case "
                                f"({core!r}; add it to house_style.PROPER if it is a "
                                f"proper noun): {ln.raw.strip()!r}")
                    break
    return hits


_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


_MONTH = ("(?:January|February|March|April|May|June|July|August|September|"
          "October|November|December)")
# "the 5th of September, 2026", "September 5, 2026", "September 5th"
_NOT_DAY_FIRST = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th) of {_MONTH}\b"
                            rf"|\b{_MONTH} \d{{1,2}}(?:st|nd|rd|th)?\b(?:, \d{{4}})?"
                            rf"|\b\d{{1,2}} {_MONTH}, \d{{4}}\b")


def iso_dates_in_prose(path):
    """WRI-007: running text spells the date out, day first, as 17 October
    2026; headings, tables and file names use ISO (a file name or a flag
    value is code, and blanked).  Paragraphs are joined first, so a date
    broken over two lines is still seen."""
    hits = [f"{rel(path)}:{ln.n}: ISO date in running text: {ln.raw.strip()[:90]!r}"
            for ln in prose_lines(path) if ln.kind == "prose" and _ISO.search(ln.text)]
    for n, text in paragraphs(path):
        for m in _NOT_DAY_FIRST.finditer(text):
            hits.append(f"{rel(path)}:{n}: date not written day first: {m.group(0)!r}")
    return hits


# "A, B, and C" / "A, B, or C": the second comma before the conjunction.
_SERIAL = re.compile(r",\s+(?:[^,.;:()–—]{1,40}?),\s+(and|or)\s")

# The heuristic finds every serial comma of the "A, B, and C" shape, but
# also many commas between clauses, which stay: so it is a report for the
# reader (and the validation's manual check), not a test.


def serial_comma_candidates(path):
    """[(line, context)] for every possible serial comma (WRI-006)."""
    out = []
    for n, text in paragraphs(path):
        for m in _SERIAL.finditer(text):
            snippet = text[max(0, m.start() - 40):m.end() + 20]
            out.append((n, snippet))
    return out


# American spellings that have a British form (WRI-004).  Text inside ‘…’ is
# left out: it may quote a program (argparse's ‘unrecognized arguments’).
AMERICAN = [
    r"\bcolou?r(?<!colour)\w*", r"\bgray\b", r"\bgrays\b", r"\bcenter\w*",
    r"\bbehavior\w*", r"\bfavor\w*", r"\bhonor(?:s|ed|ing|able)?\b", r"\bneighbor\w*",
    r"\btoward\b", r"\bafterward\b",
    r"\b(?!\w*(?:siz|priz|seiz|maiz))\w+iz(?:e|ed|es|ing|ation|ations)\b",
    r"\banalyz\w*", r"\bcatalog\b", r"\bfulfill\b", r"\bdefense\b", r"\boffense\b",
    r"\bmodeled\b", r"\bmodeling\b", r"\btraveled\b", r"\blabeled\b", r"\bcanceled\b",
    r"\bgrayscale\b", r"\bliter\b", r"\bmeter\b", r"\bmillimeter\w*",
    r"\bcentimeter\w*", r"\bdialog\b", r"\bjewelry\b", r"\bpractic(?:ed|ing)\b", r"\bpractices?\s+(?:it|them)\b",
]
_AMERICAN = re.compile("|".join(f"(?:{p})" for p in AMERICAN), re.I)
_QUOTED = re.compile(r"‘[^‘’]*?’(?![A-Za-z])|“[^”]*”")
# Proper names that look American and are not ours to change.
AMERICAN_EXEMPT = {"Serif2.003", "License"}


def american_spellings(path):
    hits = []
    for ln in prose_lines(path):
        text = _QUOTED.sub(" ", ln.text)
        for m in _AMERICAN.finditer(text):
            word = m.group(0)
            if word in AMERICAN_EXEMPT:
                continue
            hits.append(f"{rel(path)}:{ln.n}: American spelling {word!r}: {ln.raw.strip()[:90]!r}")
    return hits


CHECKS = {
    "em dash": em_dashes,
    "straight quotes": straight_quotes,
    "nested quotes": nested_quotes,
    "heading case": heading_case,
    "ISO date in prose": iso_dates_in_prose,
    "American spelling": american_spellings,
}


# ------------------------------------------------------------------ history ---
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
_SPELLED = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)? (?:of )?(" + "|".join(MONTHS) + r"),? (\d{4})\b")
_TOKEN = re.compile(r"`[^`]+`|\d+(?:[.,]\d+)*|[^\W\d_]+(?:[-'’][^\W\d_]+)*|[%×→/+=<>#]")
# Spelling pairs folded together when history is compared (WRI-004).
_SPELLING = [(re.compile(p, re.I), r) for p, r in [
    (r"\bcolor", "colour"), (r"\bgray", "grey"), (r"\bcenter", "centre"),
    (r"\bbehavior", "behaviour"), (r"\bfavor", "favour"), (r"\bneighbor", "neighbour"),
    (r"(?<=\w)iz(?=e|ed|es|ing|ation)", "is"), (r"\banalyz", "analys"),
    (r"\btoward\b", "towards"),
]]


def history_tokens(text):
    """The words, numbers and code spans of `text`, in order, with the
    house-style differences folded away: dashes, quotation marks, commas and
    all other punctuation, line breaks, letter case outside code, the date
    format and British against American spelling.  Two texts with the same
    tokens say the same thing in the same words.  Whitespace is collapsed
    first, so a code span rewrapped over a line break is still one token."""
    text = re.sub(r"\s+", " ", text)
    text = _SPELLED.sub(lambda m: f"{m.group(3)}-{MONTHS.index(m.group(2)) + 1:02d}-"
                                  f"{int(m.group(1)):02d}", text)
    out = []
    for tok in _TOKEN.findall(text):
        if tok.startswith("`"):
            out.append(tok)
            continue
        tok = tok.replace("’", "'").lower()
        for pat, rep in _SPELLING:
            tok = pat.sub(rep, tok)
        out.append(tok)
    return out


# The most words a gloss may insert in one place (TRM-001).
MAX_INSERTION = 12
# Words a gloss never needs, and that would change what a sentence claims.
_NEGATING = {"not", "no", "never", "none", "nor", "only", "partly", "without",
             "rarely", "seldom", "hardly", "except", "unless", "but"}
_CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff]")
_MACRON = re.compile(r"[āēīōūĀĒĪŌŪ]")


def is_japanese_term(token):
    """A history token that is a Japanese term: one of JAPANESE_TERMS, or
    written with kanji or kana, or romanised with a macron (dōjō, kyū)."""
    t = token.strip("`*_").lower()
    return (t in _TERMS_LOWER or bool(_CJK.search(t)) or bool(_MACRON.search(t))
            or any(part in _TERMS_LOWER for part in t.split("-")))


def restyle_problems(old, new, allowed=()):
    """What `new` changes in `old` beyond the house style (history_tokens)
    and glosses: a list of human-readable problems, empty if none.  A report
    for the manual read (check_sweep.py); history itself is compared by
    history_problems, which allows a full restyle.

    A gloss (TRM-001) is the one insertion allowed: at most MAX_INSERTION
    words straight after a Japanese term (is_japanese_term), with no number,
    no code span and no negating word.  Everything else, an inserted,
    deleted or replaced word, a changed number or code span, is a problem,
    unless it is one of `allowed`: (old words, new words) pairs, each
    recorded in the item's acceptance.md.
    """
    a, b = history_tokens(old), history_tokens(new)
    allowed = [(tuple(history_tokens(o)), tuple(history_tokens(n))) for o, n in allowed]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    problems = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        gone, added = tuple(a[i1:i2]), tuple(b[j1:j2])
        ctx = " ".join(a[max(0, i1 - 6):i1])
        if (gone, added) in allowed:
            continue
        if op == "insert":
            if not (i1 > 0 and is_japanese_term(a[i1 - 1])):
                problems.append(f"insertion not after a Japanese term, after …{ctx}: "
                                f"{' '.join(added)!r}")
            elif len(added) > MAX_INSERTION:
                problems.append(f"long insertion after …{ctx}: {' '.join(added)!r}")
            elif any(t[0].isdigit() or t.startswith("`") for t in added):
                problems.append(f"insertion with a number or code after …{ctx}: "
                                f"{' '.join(added)!r}")
            elif _NEGATING & set(added):
                problems.append(f"insertion with a negating word after …{ctx}: "
                                f"{' '.join(added)!r}")
            continue
        problems.append(f"{op} after …{ctx}: {' '.join(gone)!r} -> {' '.join(added)!r}")
    return problems


_BOLD = re.compile(r"\*\*(.+?)\*\*")
_QUOTE = re.compile(r'"([^"]+)"|\u2018(.+?)\u2019(?![^\W\d_])')
_LINK = re.compile(r"\]\(([^)]*)\)")
# Program output quoted in history; it must survive like a title.
PROGRAM_OUTPUT = [("unknown", "variant"), ("unrecognised", "arguments")]


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _phrase(text):
    """A title or quotation as comparable words (history_tokens)."""
    return tuple(history_tokens(text))


def titles(text):
    """Every entry heading's title and every bold item title in `text`, as
    words: what the log's own quotations refer to."""
    out = [_phrase(re.sub(r"^## (\d{4}-\d{2}-\d{2} [–—] )?", "", h))
           for h in re.findall(r"^## .*$", text, re.M)]
    out += [_phrase(m.group(1)) for m in _BOLD.finditer(_flat(_CODE_SPAN.sub(" ", text)))]
    return [t for t in out if t]


def _quotes(text):
    text = _flat(_CODE_SPAN.sub(" ", text))
    return [_phrase(m.group(1) or m.group(2)) for m in _QUOTE.finditer(text)]


def _is_prefix(short, long_):
    return len(short) <= len(long_) and long_[:len(short)] == short


def entry_facts(block, all_titles):
    """What a full restyle must leave in a DECISIONS.md block (Q-1, AC-10):

    - numbers: every number, dates folded to ISO (a multiset);
    - spans: every code span, whitespace collapsed (a multiset);
    - links: every link target;
    - references: every quotation of a title (an entry heading or a bold
      item title, by its opening words) or of program output;
    - cjk: every run of kanji or kana, code included, in order (compared by
      cjk_lost, since a gloss may add one);
    - referenced: every bold item title that a quotation anywhere in the
      log refers to, word for word (in history_problems).
    """
    flat = _flat(block)
    spans = sorted(_flat(m.group(2)) for m in re.finditer(r"(`+)([^`]+?)\1", flat))
    plain = re.sub(r"(`+)([^`]+?)\1", " ", flat)
    links = sorted(_LINK.findall(plain))
    plain = _SPELLED.sub(lambda m: f"{m.group(3)}-{MONTHS.index(m.group(2)) + 1:02d}-"
                                   f"{int(m.group(1)):02d}", _LINK.sub("]", plain))
    numbers = sorted(re.findall(r"\d+(?:\.\d+)?", plain))
    refs = sorted(q for q in _quotes(block)
                  if q in PROGRAM_OUTPUT or any(_is_prefix(q, t) for t in all_titles))
    return {"numbers": numbers, "spans": spans, "links": links, "references": refs,
            "cjk": cjk_runs(block)}


# Kanji, kana (with ・ and ー), 々, 〇 and the supplementary ideographs (𠮷).
_CJK_RUN = re.compile("[\u3005\u3007\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff"
                      "\U00020000-\U0002ffff]+")


def cjk_runs(text):
    """Every run of Japanese characters in `text`, in order."""
    return _CJK_RUN.findall(text)


def cjk_lost(before, now):
    """What became of the runs of `before` (cjk_runs) in `now`: [] if they
    all come back in the same order, with runs added anywhere (a gloss can
    bring 弐 or 大字).  Otherwise the runs lost, counting repeats, or, if
    none is lost, the first run out of order (初段 and 一段 swapped)."""
    lost = sorted((Counter(before) - Counter(now)).elements())
    if lost:
        return lost
    j = 0                       # walk `now` once; each run must lie ahead
    for r in before:
        while j < len(now) and now[j] != r:
            j += 1
        if j == len(now):
            return [f"{r} (out of order)"]
        j += 1
    return []


def _markers(block):
    """Decisions an entry states: top-level bullets and bold-led paragraphs."""
    return len(re.findall(r"^(?:- |\*\*)", block, re.M))


def _words(block):
    return len(history_tokens(block))


# A restyle may add glosses but not a new decision: an entry may grow by
# this much at most (words), on top of GROWTH_WORDS.
GROWTH_FACTOR = 1.15
GROWTH_WORDS = 25


# Edits to history that an item's contract allowed after the fact.  Each is
# (item slug, the commit that made the edit, pattern): the region the
# pattern matches is set aside on both sides when history_problems compares
# against a baseline from before that commit.  Against a baseline that
# already has the edit, the region is compared like everything else.  A
# later item that may change an old entry adds one line here (and the tester
# re-pins, AC-11).
HISTORY_EDITS = [
    # The flag-removal item (its AC-10, user-approved): the last two bullets
    # of the 2026-09-05 output entry, reworded into the past tense.  The
    # flag's name, and so the slug, is split: that item's AC-11 bans it from
    # the repository.
    ("remove-super" "sample", "8509b85",
     re.compile(r"^- \*\*`--super" r"sample` .*?(?=\n\n## 2026-09-05 [–—] Printing the three"
                r" hand slots\n)", re.M | re.S)),
]


def _has_commit(baseline, commit):
    """Whether `baseline` already contains `commit`; None without git (or an
    unknown ref)."""
    try:
        r = subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor",
                            commit, baseline], capture_output=True)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)


def edits_before(baseline):
    """The HISTORY_EDITS a comparison against `baseline` sets aside: those
    made after it.  Without a baseline or without git, all of them."""
    if baseline is None:
        return list(HISTORY_EDITS)
    return [e for e in HISTORY_EDITS if _has_commit(baseline, e[1]) is not True]


def _set_aside(text, edits):
    for slug, _, pattern in edits:
        text = pattern.sub(f"<edited by {slug}>", text)
    return text


def decisions_blocks(text):
    """DECISIONS.md up to `## Open`, split into the preamble (title and
    introduction) and one block per dated entry, in order.  The blocks
    joined give the text back."""
    body = text.split("\n## Open\n", 1)[0]
    return re.split(r"^(?=## )", body, flags=re.M)


def history_problems(old, new, strip=None, baseline=None):
    """Compare the history of DECISIONS.md as `old` has it (the preamble and
    every entry before `## Open`) with the same blocks of `new`: [] if they
    are byte for byte the same or keep every fact a full restyle must keep
    (the user's Q-1), else what changed.

    Kept: the number of blocks, their order and their dated headings (case
    and dash aside); per block, the facts of entry_facts; the bold item
    titles a quotation refers to, word for word; no more stated decisions
    (bullets, bold-led paragraphs) than before; and a length within
    GROWTH_FACTOR and GROWTH_WORDS.  Whether the meaning held is read by
    hand (acceptance.md, M-2).

    `new` may have more entries after them; those are not compared.  The
    regions of the HISTORY_EDITS made after `baseline` (the commit `old`
    comes from; edits_before) are set aside on both sides, and so is what
    `strip(text)` takes out.  Pass `baseline` whenever `old` is a commit's.
    """
    ob, nb = decisions_blocks(old), decisions_blocks(new)
    if len(nb) < len(ob):
        return [f"{len(ob) - 1} entries before, {len(nb) - 1} now"]
    problems = []
    for o, n in zip(ob[1:], nb[1:]):
        if entry_heading_key(o).lower() != entry_heading_key(n).lower():
            problems.append(f"entry heading {o.splitlines()[0]!r} is now {n.splitlines()[0]!r}")
    if problems:
        return problems
    edits = edits_before(baseline)
    o, n = _set_aside("".join(ob), edits), _set_aside("".join(nb[:len(ob)]), edits)
    if strip is not None:
        o, n = strip(o), strip(n)
    if o == n:
        return []
    ob, nb = decisions_blocks(o + "\n## Open\n"), decisions_blocks(n + "\n## Open\n")
    known = titles(o)
    referenced = {t for t in known if any(_is_prefix(q, t) for q in _quotes(o))}
    for ob_, nb_ in zip(ob, nb):
        name = ob_.splitlines()[0] if ob_.startswith("## ") else "the preamble"
        before, now = entry_facts(ob_, known), entry_facts(nb_, titles(n))
        for key in before:
            if key == "cjk":
                lost = cjk_lost(before[key], now[key])
                if lost:
                    problems.append(f"{name}: kanji or kana lost {lost[:6]}")
            elif before[key] != now[key]:
                gone = [x for x in before[key] if x not in now[key]]
                added = [x for x in now[key] if x not in before[key]]
                problems.append(f"{name}: {key} changed; gone {gone[:6]}, new {added[:6]}")
        bold_now = {_phrase(m.group(1)) for m in _BOLD.finditer(_flat(_CODE_SPAN.sub(" ", nb_)))}
        for m in _BOLD.finditer(_flat(_CODE_SPAN.sub(" ", ob_))):
            t = _phrase(m.group(1))
            if t in referenced and t not in bold_now:
                problems.append(f"{name}: the bold title {' '.join(t)!r}, which the log "
                                f"quotes, changed")
        if _markers(nb_) > _markers(ob_):
            problems.append(f"{name}: {_markers(nb_)} bullets or bold paragraphs, "
                            f"{_markers(ob_)} before (a new decision?)")
        if _words(nb_) > _words(ob_) * GROWTH_FACTOR + GROWTH_WORDS:
            problems.append(f"{name}: {_words(nb_)} words, {_words(ob_)} before")
    return problems


def decisions_entries(text):
    """The dated entries of DECISIONS.md, each a `## ` block, in order (the
    preamble and `## Open` left out)."""
    body = text.split("\n## Open\n", 1)[0]
    return [b for b in re.split(r"^(?=## )", body, flags=re.M) if b.startswith("## ")]


def entry_heading_key(block):
    """An entry's heading with the dash after the date normalised, to find
    the same entry before and after the sweep."""
    return re.sub(r"^## (\d{4}-\d{2}-\d{2}) [–—] ", r"## \1 – ",
                  block.splitlines()[0])


def entry_hash(block):
    """sha256 of an entry, its trailing blank lines ignored."""
    return hashlib.sha256(block.rstrip("\n").encode("utf-8")).hexdigest()


PIN_FILE = Path(__file__).resolve().parent / "house_style_sweep" / "decisions_history.sha256"
PINNED_BLOCKS = 21      # the preamble and the 20 entries at 3f025b9


def pinned_hashes():
    """The sha256 of every DECISIONS.md entry as the sweep left it, in order;
    None until the tester pins them at validation (pin_history.py)."""
    if not PIN_FILE.is_file():
        return None
    return [l.split()[0] for l in PIN_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


# ------------------------------------------------------------------ facts ---
def split_code(text):
    """(code blocks, prose lines): fenced and indented code blocks, each
    byte for byte, and every other non-blank line."""
    lines = text.splitlines()
    code, block, in_fence, prev_blank, in_list = [], [], False, True, False
    prose = []
    for raw in lines:
        if _FENCE.match(raw):
            block.append(raw)
            if in_fence:
                code.append("\n".join(block))
                block = []
            in_fence = not in_fence
            continue
        if in_fence:
            block.append(raw)
            continue
        indented = raw.startswith("    ") and raw.strip()
        if indented and (prev_blank or block) and not in_list:
            block.append(raw)
            prev_blank = False
            continue
        if block:
            code.append("\n".join(block))
            block = []
        if not raw.strip():
            prev_blank = True
            prose.append("")
            continue
        if _LIST_ITEM.match(raw):
            in_list = True
        elif not raw.startswith(" ") and prev_blank:
            in_list = False
        prev_blank = False
        prose.append(raw)
    if block:
        code.append("\n".join(block))
    return code, prose


def prose_text(text):
    """`text` without its code blocks, for the rewording report: backticks in
    a fenced block would otherwise pair with those outside it."""
    return "\n".join(split_code(text)[1])


def facts(text):
    """What a restyle must leave alone in a document, as comparable values:

    - code: every fenced or indented code block, byte for byte, in order;
    - spans: every inline code span (a sorted list: rewording may move one);
    - numbers: every number in the prose, dates folded to ISO (sorted);
    - targets: every link target, image and HTML tag (sorted);
    - tables: the header row of every table, cell count and code spans;
    - cjk: every run of kanji or kana in the prose, in order (compare it
      with cjk_lost, since a gloss may add one).
    """
    code, prose = split_code(text)
    prose = [l for l in prose if l]
    body = "\n".join(prose)
    span = re.compile(r"(`+)([^`]+?)\1")          # may run over a line break
    spans = sorted(re.sub(r"\s+", " ", m.group(2)) for m in span.finditer(body))
    plain = span.sub(" ", body)
    targets = sorted(re.findall(r"\]\(([^)]*)\)", plain) + _HTML_TAG.findall(plain)
                     + _AUTOLINK.findall(plain))
    plain = _HTML_TAG.sub(" ", _LINK_TARGET.sub("]", plain))
    plain = re.sub(r"\s+", " ", plain)
    plain = _SPELLED.sub(lambda m: f"{m.group(3)}-{MONTHS.index(m.group(2)) + 1:02d}-"
                                   f"{int(m.group(1)):02d}", plain)
    numbers = sorted(re.findall(r"\d+(?:\.\d+)?", plain))
    tables = [(l.count("|"), tuple(_CODE_SPAN.findall(l)))
              for l in prose if l.lstrip().startswith("|")]
    return {"code": code, "spans": spans, "numbers": numbers, "targets": targets,
            "tables": tables, "cjk": cjk_runs(body)}


# --------------------------------------------------------------- the report ---
JAPANESE_TERMS = [
    "dōjō", "dojo", "dan", "menkyo", "menjō", "menjo", "shihan", "renshi", "sumi",
    "kanji", "katakana", "romaji", "mon", "kamon", "yotsume-bishi", "kaisho",
    "mincho", "kasure", "kyū", "shodan", "jūjutsu", "ryū", "seireki", "dono",
    "賞状", "西暦", "殿", "〇〇", "大字",
]
_TERMS_LOWER = {t.lower() for t in JAPANESE_TERMS}


def first_mentions(path):
    """The first prose mention of each Japanese term, with its context: the
    input to the manual gloss check (TRM-001)."""
    seen = {}
    for n, text in paragraphs(path):
        for term in JAPANESE_TERMS:
            if term in seen:
                continue
            pat = (re.compile(re.escape(term)) if _CJK.search(term)
                   else re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])", re.I))
            m = pat.search(text)
            if m:
                seen[term] = (n, text[max(0, m.start() - 50):m.end() + 70])
    return seen


def main():
    total = 0
    for path in in_scope_files():
        for name, check in CHECKS.items():
            hits = check(path)
            total += len(hits)
            for h in hits:
                print(f"[{name}] {h}")
    print(f"\n{total} findings\n")
    for path in in_scope_files():
        for n, s in serial_comma_candidates(path):
            print(f"[serial comma?] {rel(path)}:{n}: {s!r}")
    if "--terms" in sys.argv:
        for path in in_scope_files():
            print(f"== {rel(path)}")
            for term, (n, ctx) in first_mentions(path).items():
                print(f"  {term} ({n}): …{ctx}…")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
