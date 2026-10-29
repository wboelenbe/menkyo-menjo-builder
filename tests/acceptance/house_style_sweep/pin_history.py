"""Pin the history of DECISIONS.md as the house-style sweep left it.

Writes decisions_history.sha256 beside this file: the sha256 of the
preamble and of every dated entry that existed when the sweep was planned
(3f025b9), in order.  test_ac_house_style_sweep.py::test_ac11_history_pinned
then holds them byte for byte, with or without git.

Run by the tester only.  The first time, at the sweep's validation, once
its text is final:

    uv run python tests/acceptance/house_style_sweep/pin_history.py

After that it prints the blocks whose hash changed and refuses to write
unless each is named with --allow, which an item's acceptance.md must
justify (and HISTORY_EDITS in house_style.py must cover):

    uv run python tests/acceptance/house_style_sweep/pin_history.py --allow 6 --allow 7

The file holds hashes and block numbers, never the text: the text would
trip the scans that keep removed names out of the repository.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import house_style as hs  # noqa: E402

BEFORE = "3f025b9"      # HEAD when the sweep was planned


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--allow", type=int, action="append", default=[], metavar="BLOCK",
                    help="a block number whose hash may change (repeat)")
    args = ap.parse_args(argv)

    text = (hs.REPO / "DECISIONS.md").read_text(encoding="utf-8")
    blocks = hs.decisions_blocks(text)[:hs.PINNED_BLOCKS]
    if len(blocks) != hs.PINNED_BLOCKS:
        sys.exit(f"DECISIONS.md has {len(blocks)} history blocks, expected {hs.PINNED_BLOCKS}")
    hashes = [hs.entry_hash(b) for b in blocks]

    # Never pin a history that lost a fact (AC-10); without git, say so.
    r = subprocess.run(["git", "-C", str(hs.REPO), "show", f"{BEFORE}:DECISIONS.md"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"warning: no git, history not checked against {BEFORE}")
    else:
        problems = hs.history_problems(r.stdout, text, baseline=BEFORE)
        if problems:
            print("\n".join(problems))
            sys.exit(f"refusing to pin: the history lost facts against {BEFORE}")

    old = hs.pinned_hashes()
    if old is not None:
        changed = [i for i, (o, h) in enumerate(zip(old, hashes)) if o != h]
        for i in changed:
            slugs = [slug for slug, _, pat in hs.HISTORY_EDITS
                     if pat.search(blocks[i] + (blocks[i + 1] if i + 1 < len(blocks) else ""))]
            print(f"block {i} changed: {blocks[i].splitlines()[0]!r}"
                  + (f"  HISTORY_EDITS: {', '.join(slugs)}" if slugs else "")
                  + ("" if i in args.allow else "  (not allowed)"))
        refused = [i for i in changed if i not in args.allow]
        if refused:
            sys.exit(f"refusing to re-pin: name each changed block with --allow ({refused})")
        if not changed:
            print("nothing changed")
            return

    lines = ["# sha256 of DECISIONS.md's preamble and entries after the house-style sweep;",
             "# written by pin_history.py, compared by test_ac11_history_pinned."]
    lines += [f"{h}  block {i}" for i, h in enumerate(hashes)]
    hs.PIN_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pinned {len(blocks)} blocks in {hs.rel(hs.PIN_FILE)}")


if __name__ == "__main__":
    main()
