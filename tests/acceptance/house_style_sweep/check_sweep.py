"""The house-style sweep's one-off checks against the commit before it.

Not part of the suite: later items change the README's facts and the Open
list for good reasons, so these comparisons hold only for the sweep itself.
The tester runs it at validation (acceptance.md, AC-9, AC-12, AC-15 and the
manual checks for AC-4, AC-7 and AC-8):

    uv run python tests/acceptance/house_style_sweep/check_sweep.py [BEFORE]

Exit code 1 if a fact changed, the Open list changed beyond closing the
item, or a file outside the sweep's scope changed.  The rewording report,
the serial-comma candidates and the first mention of each Japanese term
are printed for the manual review and never fail the run.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import house_style as hs  # noqa: E402

BEFORE = sys.argv[1] if len(sys.argv) > 1 else "3f025b9"
CLOSED_ITEM = re.compile(r"^- \*\*A house-style sweep.*?(?=^- \*\*|\Z)", re.M | re.S)
ALLOWED_PREFIXES = ("tests/acceptance/", "docs/work/house-style-sweep/")


def git(*args):
    return subprocess.run(["git", "-C", str(hs.REPO), *args], capture_output=True,
                          text=True, check=True).stdout


def old_text(path):
    return git("show", f"{BEFORE}:{hs.rel(path)}")


def main():
    failed = False

    print(f"== facts against {BEFORE} (AC-9)")
    for path in hs.in_scope_files():
        if path.name == "DECISIONS.md":
            continue
        before, now = hs.facts(old_text(path)), hs.facts(path.read_text(encoding="utf-8"))
        for key in before:
            if key == "cjk":
                lost = hs.cjk_lost(before[key], now[key])
                if lost:
                    failed = True
                    print(f"FAIL {hs.rel(path)}: kanji or kana lost {lost[:8]}")
            elif before[key] != now[key]:
                failed = True
                gone = [x for x in before[key] if x not in now[key]]
                new = [x for x in now[key] if x not in before[key]]
                print(f"FAIL {hs.rel(path)}: {key} changed; gone {gone[:8]}, new {new[:8]}")
    print("   done")

    print(f"== DECISIONS.md `## Open` against {BEFORE} (AC-12)")
    old_open = old_text(hs.REPO / "DECISIONS.md").split("\n## Open\n", 1)[1]
    new_open = (hs.REPO / "DECISIONS.md").read_text(encoding="utf-8").split("\n## Open\n", 1)[1]
    old_open, n = CLOSED_ITEM.subn("", old_open)
    assert n == 1, "the house-style item is not in the old Open list"
    # restyled in full like the history (Q-1): the facts stay, item by item
    items = lambda t: re.findall(r"^- \*\*.*?(?=^- \*\*|\Z)", t, re.M | re.S)
    old_items, new_items = items(old_open), items(new_open)
    if len(old_items) != len(new_items):
        failed = True
        print(f"FAIL {len(old_items)} Open items before (less the closed one), "
              f"{len(new_items)} now")
    for o, n_ in zip(old_items, new_items):
        before, now = hs.entry_facts(o, []), hs.entry_facts(n_, [])
        for key in before:
            lost = (hs.cjk_lost(before[key], now[key]) if key == "cjk"
                    else before[key] != now[key])
            if lost:
                failed = True
                print(f"FAIL Open item {o.splitlines()[0][:50]!r}: {key} changed")
    print("   done")

    print(f"== files changed since {BEFORE} (AC-15)")
    changed = set(git("diff", "--name-only", BEFORE).split())
    changed |= set(git("ls-files", "--others", "--exclude-standard").split())
    scope = {hs.rel(p) for p in hs.in_scope_files()}
    for f in sorted(changed):
        ok = f in scope or f.startswith(ALLOWED_PREFIXES)
        failed |= not ok
        print(("   " if ok else "FAIL ") + f)

    print(f"== rewording against {BEFORE}, for review (AC-8, AC-9, M-2)")
    for path in hs.in_scope_files():
        for p in hs.restyle_problems(hs.prose_text(old_text(path)),
                                     hs.prose_text(path.read_text(encoding="utf-8"))):
            print(f"   {hs.rel(path)}: {p}")

    print("== serial-comma candidates, for review (AC-4)")
    for path in hs.in_scope_files():
        for n, s in hs.serial_comma_candidates(path):
            print(f"   {hs.rel(path)}:{n}: {s!r}")

    print("== first mention of each Japanese term, for review (AC-7)")
    for path in hs.in_scope_files():
        print(f"   {hs.rel(path)}")
        for term, (n, ctx) in hs.first_mentions(path).items():
            print(f"      {term} ({n}): …{ctx}…")

    print("FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
